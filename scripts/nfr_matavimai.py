"""Nefunkcinių reikalavimų matavimai (aprašo 3 skyriui „Testavimas“).

Matuojama tuo pačiu keliu, kuriuo sistema veikia iš tikrųjų:
  NFR-03  Paskelbiamas skelbimas 200 tėvų. Laiškus siunčia tikra planuoklė (kas minutę)
          per SMTP į vietinį serverį. Planuoklė paleidžiama iškart po įvykio, todėl
          pirmasis siuntimas vyksta tik po minutės – tai blogiausias atvejis.
          Matuojama, po kiek laiko nuo įvykio gautas paskutinis laiškas (riba – 2 min.).
  NFR-04  500 eilučių XLSX failo įkėlimas, patikra ir peržiūros puslapis (riba – 10 s).
  NFR-05  Pažymos prašymo patvirtinimas su PDF sugeneravimu (riba – 3 s).

Duomenų bazė – atskira: pagal nutylėjimą laikinas SQLite failas, su --postgres –
TEST_DATABASE_URL (jos pavadinime turi būti žodis „test“). Schema sukuriama
migracijomis, todėl veikia numatytosios pranešimų taisyklės. Kūrimo duomenų bazė
(DATABASE_URL) nenaudojama ir nekeičiama.

Paleidimas projekto kataloge:
    python scripts/nfr_matavimai.py
    python scripts/nfr_matavimai.py --postgres --failas nfr_rezultatai.txt
"""
import argparse
import io
import logging
import os
import platform
import secrets
import shutil
import socketserver
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
from datetime import date, datetime
from pathlib import Path

PROJEKTO_KATALOGAS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJEKTO_KATALOGAS)

from apscheduler.schedulers.background import BackgroundScheduler  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from db_atnaujinimas import sukurti_schema_is_naujo  # noqa: E402
from models import EilesIrasas, Klase, Mokinys, PazymosPrasymas, Skelbimas, User, db  # noqa: E402
from services.importas import SABLONO_STULPELIAI  # noqa: E402
from services.ivykiai import skelbti  # noqa: E402
from services.pazymos import pateikti_prasyma  # noqa: E402
from services.planuokle import LAIKO_JUOSTA, Planuokle  # noqa: E402

KLASES = ("5A", "6A", "7A", "8A")
RIBOS = {"NFR-03": 120, "NFR-04": 10, "NFR-05": 3}  # sekundės, iš aprašo 1.3 poskyrio


class MatavimoKlaida(Exception):
    """Matavimo nepavyko atlikti (pvz., puslapis grąžino klaidą)."""


# --- Vietinis SMTP serveris -----------------------------------------------------------

class _SmtpApdorotojas(socketserver.StreamRequestHandler):
    """Tiek SMTP protokolo, kiek reikia smtplib: priima laišką ir įsimena gavimo laiką."""

    def _atsakyti(self, eilute):
        self.wfile.write(eilute.encode("ascii") + b"\r\n")

    def handle(self):
        self._atsakyti("220 matavimas ESMTP")
        duomenys = False
        for eilute in self.rfile:
            if duomenys:
                if eilute.rstrip(b"\r\n") == b".":  # laiško pabaiga
                    duomenys = False
                    self.server.gautas_laiskas()
                    self._atsakyti("250 OK")
                continue
            komanda = eilute[:4].upper()
            if komanda in (b"EHLO", b"HELO"):
                self._atsakyti("250 matavimas")
            elif komanda == b"DATA":
                duomenys = True
                self._atsakyti("354 End data with <CR><LF>.<CR><LF>")
            elif komanda == b"QUIT":
                self._atsakyti("221 Bye")
                return
            else:  # MAIL, RCPT, RSET, NOOP
                self._atsakyti("250 OK")


class VietinisSmtpServeris(socketserver.ThreadingTCPServer):
    """SMTP serveris atsitiktiniame prievade; kiekvienam laiškui įrašo gavimo laiką."""

    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), _SmtpApdorotojas)
        self.gavimo_laikai = []
        self.laukiama = 0
        self.visi_gauti = threading.Event()
        self._uzraktas = threading.Lock()

    @property
    def prievadas(self):
        return self.server_address[1]

    def laukti(self, kiekis):
        with self._uzraktas:
            self.gavimo_laikai, self.laukiama = [], kiekis
            self.visi_gauti.clear()

    def gautas_laiskas(self):
        with self._uzraktas:
            self.gavimo_laikai.append(time.perf_counter())
            if len(self.gavimo_laikai) >= self.laukiama:
                self.visi_gauti.set()


# --- Aplinka -----------------------------------------------------------------------------

def duomenu_bazes_adresas(postgres, katalogas):
    if not postgres:
        return "sqlite:///" + (Path(katalogas) / "matavimas.db").as_posix()
    adresas = os.environ.get("TEST_DATABASE_URL")
    if not adresas:
        raise SystemExit("Nenurodytas TEST_DATABASE_URL (žr. .env.example).")
    url = make_url(adresas)
    if not url.drivername.startswith("postgresql") or "test" not in (url.database or ""):
        raise SystemExit("TEST_DATABASE_URL turi būti PostgreSQL duomenų bazė, kurios pavadinime yra žodis „test“.")
    return adresas


def sukurti_programa(db_adresas, katalogas, smtp_prievadas):
    class MatavimoKonfiguracija(TestConfig):
        SQLALCHEMY_DATABASE_URI = db_adresas
        UPLOAD_FOLDER = os.path.join(katalogas, "ikelti")
        DOKUMENTU_KATALOGAS = os.path.join(katalogas, "dokumentai")
        MAIL_FAILU_KATALOGAS = os.path.join(katalogas, "laiskai")
        MAIL_BACKEND = "smtp"
        MAIL_SERVER = "127.0.0.1"
        MAIL_PORT = smtp_prievadas
        MAIL_USE_TLS = False
        MAIL_USE_SSL = False
        MAIL_USERNAME = None
        MAIL_PASSWORD = None

    return create_app(MatavimoKonfiguracija)


def duomenu_bazes_pavadinimas():
    if db.engine.dialect.name == "postgresql":
        versija = db.session.execute(text("SHOW server_version")).scalar()
        return f"PostgreSQL {versija.split()[0]} ({db.engine.url.database})"
    return f"SQLite {sqlite3.sqlite_version} (laikinas failas)"


def paruosti_duomenis():
    """Administratorius su atsitiktiniu slaptažodžiu (niekur nerodomas) ir klasės."""
    slaptazodis = secrets.token_urlsafe(16)
    admin = User(vardas="Matavimų", pavarde="Administratorius", email="admin@matavimas.lt",
                 role="administratorius")
    admin.nustatyti_slaptazodi(slaptazodis)
    db.session.add(admin)
    db.session.add_all([Klase(pavadinimas=p, mokslo_metai="2026-2027") for p in KLASES])
    db.session.commit()
    return admin, slaptazodis


def prisijungti(programa, admin, slaptazodis):
    klientas = programa.test_client()
    atsakymas = klientas.post("/login", data={"email": admin.email, "slaptazodis": slaptazodis})
    if atsakymas.status_code != 302:
        raise MatavimoKlaida("Nepavyko prisijungti administratoriumi.")
    return klientas


# --- NFR-03: pranešimų siuntimas ----------------------------------------------------------

def matuoti_siuntima(programa, smtp, autorius, tevu_sk):
    slaptazodzio_maisa = generate_password_hash(secrets.token_urlsafe(16))
    db.session.add_all([
        User(vardas=f"Tėvas{i:03d}", pavarde="Matavimas", email=f"tevas{i:03d}@matavimas.lt",
             role="tevas", slaptazodzio_hash=slaptazodzio_maisa)
        for i in range(tevu_sk)
    ])
    db.session.commit()

    ivykis = time.perf_counter()
    skelbimas = Skelbimas(pavadinimas="Tėvų susirinkimas", turinys="Kviečiame į visuotinį tėvų susirinkimą.",
                          matomas_tevams=True, vartotojo_id=autorius.id)
    db.session.add(skelbimas)
    db.session.flush()
    skelbti("skelbimas_paskelbtas", skelbimas)
    db.session.commit()
    irasymas = time.perf_counter() - ivykis

    eileje = EilesIrasas.query.filter_by(kanalas="el_pastas", busena=EilesIrasas.LAUKIA).count()
    db.session.commit()
    if not eileje:
        raise MatavimoKlaida("Skelbimas nesukūrė el. laiškų – patikrinkite taisyklę „Naujas skelbimas tėvams“.")
    smtp.laukti(eileje)

    print(f"  Eilėje {eileje} laiškų. Laukiama, kol planuoklė juos išsiųs (apie 1 min.)...", flush=True)
    planuokle = Planuokle(programa, BackgroundScheduler(timezone=LAIKO_JUOSTA))
    planuokle.registruoti_uzduotis()
    planuokle.planuokle.start()
    try:
        smtp.visi_gauti.wait(timeout=RIBOS["NFR-03"] + 120)
    finally:
        planuokle.planuokle.shutdown(wait=True)

    laikai = sorted(t - ivykis for t in smtp.gavimo_laikai)
    issiusta = EilesIrasas.query.filter_by(kanalas="el_pastas", busena=EilesIrasas.ISSIUSTAS).count()
    db.session.commit()
    return {"eileje": eileje, "gauta": len(laikai), "issiusta": issiusta, "irasymas": irasymas,
            "pirmas": laikai[0] if laikai else None, "paskutinis": laikai[-1] if laikai else None}


# --- NFR-04: importo patikra ir peržiūra ---------------------------------------------------

def importo_failas(eiluciu_sk=500):
    """XLSX pagal sistemos šabloną; kas 50-a eilutė su klaida, kad peržiūroje būtų ką rodyti."""
    knyga = Workbook()
    lapas = knyga.active
    lapas.append([pavadinimas for _, pavadinimas in SABLONO_STULPELIAI[:6]])
    for i in range(eiluciu_sk):
        gimimo_data = "2015-13-01" if i % 50 == 49 else f"{2010 + i % 10}-{1 + i % 12:02d}-{1 + i % 28:02d}"
        lapas.append([f"Vardas{i:03d}", f"Pavardė{i:03d}", gimimo_data, KLASES[i % len(KLASES)],
                      f"Tėvas Pavardė{i:03d}", f"tevas{i:03d}@pastas.lt"])
    buferis = io.BytesIO()
    knyga.save(buferis)
    return buferis.getvalue()


def matuoti_importa(klientas, kartai):
    turinys = importo_failas()
    trukmes = []
    for k in range(kartai):
        pradzia = time.perf_counter()
        atsakymas = klientas.post("/importas/", data={"failas": (io.BytesIO(turinys), f"mokiniai_{k + 1}.xlsx")},
                                  content_type="multipart/form-data", follow_redirects=True)
        trukmes.append(time.perf_counter() - pradzia)
        if atsakymas.status_code != 200 or not atsakymas.request.path.endswith("/perziura"):
            raise MatavimoKlaida(f"Importo peržiūra neatidaryta (atsakymo kodas {atsakymas.status_code}).")
    return trukmes


# --- NFR-05: pažymos PDF ------------------------------------------------------------------

def matuoti_pazymas(klientas, kartai):
    mokinys = Mokinys(vardas="Ugnė", pavarde="Kairytė", gimimo_data=date(2015, 3, 21),
                      klases_id=Klase.query.filter_by(pavadinimas="5A").one().id)
    tevas = User(vardas="Rasa", pavarde="Kairienė", email="rasa@matavimas.lt", role="tevas",
                 slaptazodzio_hash=generate_password_hash(secrets.token_urlsafe(16)))
    db.session.add_all([mokinys, tevas])
    db.session.commit()
    tevas.vaikai = [mokinys]
    db.session.commit()

    trukmes = []
    for _ in range(kartai):
        prasymas = pateikti_prasyma(tevas, mokinys, "Pateikti „Sodrai“")
        pradzia = time.perf_counter()
        atsakymas = klientas.post(f"/dokumentai/prasymai/{prasymas.id}/patvirtinti")
        trukmes.append(time.perf_counter() - pradzia)
        if atsakymas.status_code != 302 or prasymas.busena != PazymosPrasymas.IVYKDYTAS:
            raise MatavimoKlaida("Pažyma nesugeneruota.")
    return trukmes


# --- Ataskaita ------------------------------------------------------------------------------

def sek(reiksme):
    return f"{reiksme:.2f} s".replace(".", ",")


def eilute(kodas, aprasymas, ismatuota):
    atitinka = ismatuota is not None and ismatuota <= RIBOS[kodas]
    reiksme = sek(ismatuota) if ismatuota is not None else "–"
    return (f"{kodas}  {aprasymas:<58} {reiksme:>9}   riba {RIBOS[kodas]} s   "
            f"{'Atitinka' if atitinka else 'Neatitinka'}"), atitinka


def main():
    parser = argparse.ArgumentParser(description="Nefunkcinių reikalavimų NFR-03, NFR-04, NFR-05 matavimai")
    parser.add_argument("--postgres", action="store_true", help="naudoti TEST_DATABASE_URL vietoj SQLite")
    parser.add_argument("--tevu", type=int, default=200, help="laiškų gavėjų skaičius NFR-03 (200)")
    parser.add_argument("--importu", type=int, default=3, help="kiek kartų matuoti importą (3)")
    parser.add_argument("--pazymu", type=int, default=10, help="kiek pažymų sugeneruoti (10)")
    parser.add_argument("--be-siuntimo", action="store_true", help="praleisti NFR-03 (trunka apie minutę)")
    parser.add_argument("--failas", help="rezultatus papildomai įrašyti į šį tekstinį failą")
    argumentai = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    katalogas = tempfile.mkdtemp(prefix="nfr_matavimai_")
    smtp = VietinisSmtpServeris()
    threading.Thread(target=smtp.serve_forever, daemon=True).start()
    programa = sukurti_programa(duomenu_bazes_adresas(argumentai.postgres, katalogas), katalogas, smtp.prievadas)

    rezultatai, visi_atitinka = [], True
    try:
        with programa.app_context():
            print("Kuriama matavimų duomenų bazė (migracijos)...", flush=True)
            sukurti_schema_is_naujo()
            logging.getLogger("alembic").setLevel(logging.WARNING)
            admin, slaptazodis = paruosti_duomenis()
            klientas = prisijungti(programa, admin, slaptazodis)
            aplinka = (f"Aplinka: {platform.platform()}, Python {platform.python_version()}, "
                       f"{os.cpu_count()} loginiai procesoriai, {duomenu_bazes_pavadinimas()}")

            if not argumentai.be_siuntimo:
                print("NFR-03: skelbimas tėvams ir pranešimų siuntimas...", flush=True)
                s = matuoti_siuntima(programa, smtp, admin, argumentai.tevu)
                tekstas, atitinka = eilute(
                    "NFR-03", f"Skelbimas {s['eileje']} tėvų: paskutinis laiškas po įvykio",
                    s["paskutinis"] if s["gauta"] == s["eileje"] else None)
                rezultatai.append(tekstas)
                rezultatai.append(f"        gauta SMTP serveryje {s['gauta']} iš {s['eileje']}, "
                                  f"eilėje pažymėta „Išsiųstas“ {s['issiusta']}")
                rezultatai.append(f"        įvykio įrašymas su {s['eileje']} pranešimų: {sek(s['irasymas'])}")
                if s["gauta"]:
                    rezultatai.append(f"        laukimas iki planuoklės paleidimo: pirmasis laiškas po "
                                      f"{sek(s['pirmas'])}, visi išsiųsti per {sek(s['paskutinis'] - s['pirmas'])}")
                visi_atitinka &= atitinka

            print("NFR-04: 500 eilučių XLSX įkėlimas ir peržiūra...", flush=True)
            trukmes = matuoti_importa(klientas, argumentai.importu)
            tekstas, atitinka = eilute("NFR-04", f"500 eilučių XLSX patikra ir peržiūra (blogiausias iš {len(trukmes)})",
                                       max(trukmes))
            rezultatai.append(tekstas)
            rezultatai.append(f"        vidurkis {sek(statistics.mean(trukmes))}, mažiausia {sek(min(trukmes))}")
            visi_atitinka &= atitinka

            print("NFR-05: pažymų PDF generavimas...", flush=True)
            trukmes = matuoti_pazymas(klientas, argumentai.pazymu)
            tekstas, atitinka = eilute("NFR-05", f"Pažymos patvirtinimas su PDF (blogiausias iš {len(trukmes)})",
                                       max(trukmes))
            rezultatai.append(tekstas)
            rezultatai.append(f"        pirmoji (su šrifto įkėlimu) {sek(trukmes[0])}, "
                              f"vidurkis {sek(statistics.mean(trukmes))}")
            visi_atitinka &= atitinka

            db.session.remove()
            db.engine.dispose()
    finally:
        smtp.shutdown()
        smtp.server_close()
        shutil.rmtree(katalogas, ignore_errors=True)

    ataskaita = "\n".join([
        "",
        f"Nefunkcinių reikalavimų matavimai – {datetime.now():%Y-%m-%d %H:%M}",
        aplinka,
        "",
        *rezultatai,
        "",
        "Visi išmatuoti reikalavimai įvykdyti." if visi_atitinka else "DĖMESIO: ne visi reikalavimai įvykdyti.",
    ])
    print(ataskaita)
    if argumentai.failas:
        Path(argumentai.failas).write_text(ataskaita.lstrip() + "\n", encoding="utf-8")
        print(f"\nRezultatai įrašyti į {argumentai.failas}")
    return 0 if visi_atitinka else 1


if __name__ == "__main__":
    sys.exit(main())
