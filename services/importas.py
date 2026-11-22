"""Masinis mokinių ir tėvų importas iš XLSX ar CSV (aprašo 6 pav. ImportoVykdytojas,
EiluciuTikrintojas; FR-I01–FR-I07, NFR-04, NFR-08).

Importas vyksta dviem etapais (aprašo 4 pav.):
1) nuskaityti() ir tikrinti(): failo eilutės su tikrinimo rezultatais įrašomos į
   importo_eilutes – administratorius mato peržiūrą, mokiniai dar nekuriami;
2) irasyti(): patvirtinus, tinkamos eilutės, naujos tėvų paskyros ir kvietimų
   laiškai įrašomi VIENA transakcija. Įvykus klaidai neįrašoma nė viena eilutė.

Saugumas: tik .xlsx ir .csv, iki 2 MB ir 1000 eilučių; XLSX turinys tikrinamas
(ZIP parašas) ir skaitomas su data_only=True – formulės nevykdomos (NFR-08).
"""
import csv
import io
import re
import unicodedata
from datetime import date, datetime

from openpyxl import load_workbook

from models import ImportoEilute, ImportoSesija, Klase, Mokinys, User, db
from services.ivykiai import skelbti
from services.paskyros import atsitiktinis_slaptazodis

DIDZIAUSIAS_DYDIS = 2 * 1024 * 1024
DIDZIAUSIAS_EILUCIU_SK = 1000
PRIVALOMI = ("vardas", "pavarde", "gimimo_data", "klase")

# Šablono stulpeliai (FR-I01): (raktas, antraštė šablone)
SABLONO_STULPELIAI = (
    ("vardas", "Vardas"),
    ("pavarde", "Pavardė"),
    ("gimimo_data", "Gimimo data"),
    ("klase", "Klasė"),
    ("tevo_vardas", "Tėvo (globėjo) vardas, pavardė"),
    ("tevo_el_pastas", "Tėvo (globėjo) el. paštas"),
    ("tevo_telefonas", "Tėvo (globėjo) telefonas"),
    ("adresas", "Adresas"),
    ("autobusas", "Mokyklos autobusas"),
)
# Antraštės sinonimai po normalizavimo (mažosios raidės, be diakritikų)
_SINONIMAI = {
    "vardas": "vardas", "pavarde": "pavarde", "gimimo_data": "gimimo_data", "klase": "klase",
    "tevo_globejo_vardas_pavarde": "tevo_vardas", "tevo_vardas_pavarde": "tevo_vardas", "tevo_vardas": "tevo_vardas",
    "tevo_globejo_el_pastas": "tevo_el_pastas", "tevo_el_pastas": "tevo_el_pastas", "el_pastas": "tevo_el_pastas",
    "tevo_globejo_telefonas": "tevo_telefonas", "tevo_telefonas": "tevo_telefonas", "telefonas": "tevo_telefonas",
    "adresas": "adresas", "mokyklos_autobusas": "autobusas", "autobusas": "autobusas",
}
EL_PASTO_FORMATAS = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class ImportoKlaida(Exception):
    """Viso failo klaida (netinkamas formatas, per didelis, trūksta stulpelių)."""


def _normalizuoti_antraste(tekstas):
    be_diakritiku = unicodedata.normalize("NFKD", str(tekstas or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", be_diakritiku.lower()).strip("_")


def _tekstas(reiksme):
    """Langelio reikšmė -> tekstas (datos MMMM-MM-DD, sveikieji skaičiai be .0)."""
    if reiksme is None:
        return ""
    if isinstance(reiksme, (datetime, date)):
        return reiksme.strftime("%Y-%m-%d")
    if isinstance(reiksme, float) and reiksme.is_integer():
        return str(int(reiksme))
    return str(reiksme).strip()


def _vardo_raktas(vardas, pavarde, gimimo_data):
    return (vardas.strip().lower(), pavarde.strip().lower(), gimimo_data.strip())


class EiluciuTikrintojas:
    """Eilučių tikrinimas be failų ir be įrašymo – jį lengva testuoti atskirai."""

    def __init__(self, klasiu_pavadinimai, esami_mokiniai):
        self.klases = {k.lower() for k in klasiu_pavadinimai}
        self.esami = esami_mokiniai  # aibė (vardas, pavarde, gimimo data) mažosiomis raidėmis

    def tikrinti(self, eilute):
        """FR-I02: grąžina klaidų sąrašą (tuščias – eilutė tinkama)."""
        klaidos = []
        if not eilute.get("vardas"):
            klaidos.append("Nenurodytas vardas")
        if not eilute.get("pavarde"):
            klaidos.append("Nenurodyta pavardė")
        klase = eilute.get("klase", "")
        if not klase:
            klaidos.append("Nenurodyta klasė")
        elif klase.lower() not in self.klases:
            klaidos.append(f"Klasė „{klase}“ nerasta")
        try:
            datetime.strptime(eilute.get("gimimo_data", ""), "%Y-%m-%d")
        except ValueError:
            klaidos.append("Neteisinga gimimo data (reikia MMMM-MM-DD)")
        el_pastas = eilute.get("tevo_el_pastas", "")
        if el_pastas and not EL_PASTO_FORMATAS.match(el_pastas):
            klaidos.append("Neteisingas el. paštas")
        return klaidos

    def rasti_dublikatus(self, eilutes):
        """FR-I03: {eilutės nr.: priežastis} – sutampa vardas, pavardė ir gimimo data
        su mokiniu sistemoje arba su ankstesne to paties failo eilute."""
        dublikatai, matyti = {}, set()
        for nr, eilute in eilutes:
            raktas = _vardo_raktas(eilute.get("vardas", ""), eilute.get("pavarde", ""), eilute.get("gimimo_data", ""))
            if raktas in self.esami:
                dublikatai[nr] = "Jau yra sistemoje"
            elif raktas in matyti:
                dublikatai[nr] = "Pasikartoja faile"
            matyti.add(raktas)
        return dublikatai


class ImportoVykdytojas:
    """Failo nuskaitymas, tikrinimas ir įrašymas (aprašo 6 pav.)."""

    # --- 1 etapas: nuskaitymas ------------------------------------------------------

    def nuskaityti(self, failo_vardas, turinys, naudotojas):
        """FR-I01: failas -> ImportoSesija su eilutėmis (dar nepatikrintomis)."""
        if len(turinys) > DIDZIAUSIAS_DYDIS:
            raise ImportoKlaida("Failas per didelis: leidžiama iki 2 MB.")
        pletinys = failo_vardas.rsplit(".", 1)[-1].lower() if "." in failo_vardas else ""
        if pletinys == "xlsx":
            antrastes, eilutes = self._skaityti_xlsx(turinys)
        elif pletinys == "csv":
            antrastes, eilutes = self._skaityti_csv(turinys)
        else:
            raise ImportoKlaida("Tinka tik .xlsx arba .csv failai.")

        stulpeliai = [_SINONIMAI.get(_normalizuoti_antraste(a)) for a in antrastes]
        truksta = [k for k in PRIVALOMI if k not in stulpeliai]
        if truksta:
            pavadinimai = dict(SABLONO_STULPELIAI)
            raise ImportoKlaida("Trūksta privalomų stulpelių: " + ", ".join(pavadinimai[k] for k in truksta) +
                                ". Naudokite sistemoje pateiktą šabloną.")
        duomenu_eilutes = [e for e in eilutes if any(_tekstas(r) for r in e)]
        if not duomenu_eilutes:
            raise ImportoKlaida("Faile nėra duomenų eilučių.")
        if len(duomenu_eilutes) > DIDZIAUSIAS_EILUCIU_SK:
            raise ImportoKlaida(f"Per daug eilučių: leidžiama iki {DIDZIAUSIAS_EILUCIU_SK}.")

        sesija = ImportoSesija(vartotojo_id=naudotojas.id, failo_vardas=failo_vardas[:255],
                               eiluciu_sk=len(duomenu_eilutes))
        nr = 1  # 1-oji eilutė – antraštė
        for eilute in eilutes:
            nr += 1
            if not any(_tekstas(r) for r in eilute):
                continue
            duomenys = {raktas: _tekstas(reiksme) for raktas, reiksme in zip(stulpeliai, eilute) if raktas}
            sesija.eilutes.append(ImportoEilute(eilutes_nr=nr, duomenys=duomenys, busena=ImportoEilute.TINKAMA))
        db.session.add(sesija)
        return sesija

    @staticmethod
    def _skaityti_xlsx(turinys):
        if not turinys.startswith(b"PK\x03\x04"):  # XLSX yra ZIP archyvas
            raise ImportoKlaida("Failo turinys neatitinka XLSX formato.")
        try:
            knyga = load_workbook(io.BytesIO(turinys), read_only=True, data_only=True)
        except Exception as klaida:
            raise ImportoKlaida("XLSX failo nepavyko perskaityti.") from klaida
        lapas = knyga.worksheets[0]
        eilutes = [list(eilute) for eilute in lapas.iter_rows(values_only=True)]
        knyga.close()
        if not eilutes:
            raise ImportoKlaida("Failas tuščias.")
        return [_tekstas(a) for a in eilutes[0]], eilutes[1:]

    @staticmethod
    def _skaityti_csv(turinys):
        for koduote in ("utf-8-sig", "cp1257"):  # „Excel“ lietuviškai dažnai išsaugo cp1257
            try:
                tekstas = turinys.decode(koduote)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ImportoKlaida("CSV failo koduotė neatpažinta (naudokite UTF-8).")
        if "\x00" in tekstas:
            raise ImportoKlaida("Failo turinys neatitinka CSV formato.")
        skirtukas = ";" if tekstas.split("\n", 1)[0].count(";") >= tekstas.split("\n", 1)[0].count(",") else ","
        eilutes = list(csv.reader(io.StringIO(tekstas), delimiter=skirtukas))
        if not eilutes:
            raise ImportoKlaida("Failas tuščias.")
        return eilutes[0], eilutes[1:]

    # --- 1 etapas: tikrinimas -------------------------------------------------------

    def tikrinti(self, sesija):
        """FR-I02, FR-I03: kiekvienai eilutei – būsena ir klaidos; suvestinė sesijoje."""
        esami = {_vardo_raktas(m.vardas, m.pavarde, m.gimimo_data.isoformat())
                 for m in Mokinys.query.filter(Mokinys.gimimo_data.isnot(None))}
        tikrintojas = EiluciuTikrintojas([k.pavadinimas for k in Klase.query], esami)
        neirasytos = [e for e in sesija.eilutes if e.busena != ImportoEilute.IRASYTA]
        dublikatai = tikrintojas.rasti_dublikatus([(e.eilutes_nr, e.duomenys) for e in neirasytos])
        for eilute in neirasytos:
            klaidos = tikrintojas.tikrinti(eilute.duomenys)
            if klaidos:
                eilute.busena, eilute.klaidos = ImportoEilute.KLAIDA, "\n".join(klaidos)
            elif eilute.eilutes_nr in dublikatai:
                eilute.busena, eilute.klaidos = ImportoEilute.DUBLIKATAS, dublikatai[eilute.eilutes_nr]
            else:
                eilute.busena, eilute.klaidos = ImportoEilute.TINKAMA, None
        sesija.tinkamu_sk = sum(1 for e in sesija.eilutes if e.busena == ImportoEilute.TINKAMA)
        sesija.klaidu_sk = sum(1 for e in sesija.eilutes if e.busena == ImportoEilute.KLAIDA)
        return sesija

    # --- 2 etapas: įrašymas viena transakcija (FR-I05, FR-I06) --------------------

    def irasyti(self, sesija, naudotojas):
        if sesija.busena != ImportoSesija.PATIKRINTA:
            raise ImportoKlaida("Šis importas jau užbaigtas arba atšauktas.")
        self.tikrinti(sesija)  # duomenys galėjo pasikeisti nuo peržiūros
        klases = {k.pavadinimas.lower(): k for k in Klase.query}
        tevai = {}
        try:
            for eilute in sesija.eilutes:
                if eilute.busena != ImportoEilute.TINKAMA:
                    continue
                d = eilute.duomenys
                mokinys = Mokinys(
                    vardas=d["vardas"], pavarde=d["pavarde"],
                    gimimo_data=datetime.strptime(d["gimimo_data"], "%Y-%m-%d").date(),
                    klases_id=klases[d["klase"].lower()].id,
                    adresas=d.get("adresas") or None,
                    tevo_vardas=d.get("tevo_vardas") or None,
                    tevo_email=d.get("tevo_el_pastas") or None,
                    tevo_telefonas=d.get("tevo_telefonas") or None,
                    mokyklos_autobusas=(d.get("autobusas", "").lower() in ("taip", "1", "true", "yes")),
                )
                db.session.add(mokinys)
                if d.get("tevo_el_pastas"):
                    tevas = self._tevo_paskyra(d, tevai)
                    if tevas is not None:
                        tevas.vaikai.append(mokinys)
                db.session.flush()
                eilute.busena, eilute.mokinio_id = ImportoEilute.IRASYTA, mokinys.id

            for tevas in tevai.values():  # kvietimai įrašomi į eilę toje pačioje transakcijoje
                if getattr(tevas, "_naujas", False):
                    skelbti("tevo_paskyra_sukurta", tevas)
            sesija.busena = ImportoSesija.IMPORTUOTA
            skelbti("importas_baigtas", sesija)
            db.session.commit()
        except Exception:
            db.session.rollback()  # neįrašoma nė viena eilutė
            sesija = db.session.get(ImportoSesija, sesija.id)
            sesija.busena = ImportoSesija.KLAIDA
            db.session.commit()
            raise
        return sesija

    @staticmethod
    def _tevo_paskyra(duomenys, tevai):
        """Esama tėvo paskyra arba nauja (be žinomo slaptažodžio – jį susikurs per kvietimą)."""
        el_pastas = duomenys["tevo_el_pastas"].strip().lower()
        if el_pastas in tevai:
            return tevai[el_pastas]
        naudotojas = User.query.filter(db.func.lower(User.email) == el_pastas).first()
        if naudotojas is not None and not naudotojas.yra_tevas:
            return None  # darbuotojo paskyra – vaikas automatiškai nepriskiriamas
        if naudotojas is None:
            vardas, _, pavarde = (duomenys.get("tevo_vardas") or "Tėvas").partition(" ")
            naudotojas = User(vardas=vardas[:80], pavarde=pavarde[:80], email=el_pastas, role="tevas",
                              telefonas=duomenys.get("tevo_telefonas") or None)
            naudotojas.nustatyti_slaptazodi(atsitiktinis_slaptazodis())
            naudotojas._naujas = True
            db.session.add(naudotojas)
            db.session.flush()
        tevai[el_pastas] = naudotojas
        return naudotojas


def ataskaitos_csv(sesija):
    """FR-I07: importo ataskaita CSV formatu. Reikšmės, prasidedančios =, +, -, @, pažymimos
    apostrofu, kad „Excel“ jų nevykdytų kaip formulių."""
    def saugu(reiksme):
        reiksme = str(reiksme or "")
        return "'" + reiksme if reiksme[:1] in ("=", "+", "-", "@") else reiksme

    buferis = io.StringIO()
    buferis.write("\ufeff")  # UTF-8 BOM, kad Excel teisingai rodytų lietuviškas raides
    rasytojas = csv.writer(buferis, delimiter=";")
    rasytojas.writerow(["Eilutė", "Vardas", "Pavardė", "Klasė", "Rezultatas", "Pastabos"])
    for e in sesija.eilutes:
        d = e.duomenys
        rasytojas.writerow([e.eilutes_nr, saugu(d.get("vardas")), saugu(d.get("pavarde")), saugu(d.get("klase")),
                            e.busenos_pavadinimas, saugu((e.klaidos or "").replace("\n", "; "))])
    return buferis.getvalue()


def sablono_xlsx():
    """FR-I01: importo šablonas su pavyzdine eilute."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    knyga = Workbook()
    lapas = knyga.active
    lapas.title = "Mokiniai"
    lapas.append([antraste for _, antraste in SABLONO_STULPELIAI])
    for langelis in lapas[1]:
        langelis.font = Font(bold=True, color="FFFFFF")
        langelis.fill = PatternFill("solid", fgColor="881337")
    lapas.append(["Ugnė", "Kairytė", "2015-03-21", "5A", "Rasa Kairienė", "rasa.kairiene@pastas.lt",
                  "+370 600 00000", "Noriūnų k., Kupiškio r.", "Taip"])
    for stulpelis, plotis in zip("ABCDEFGHI", (14, 16, 14, 8, 28, 30, 18, 28, 18)):
        lapas.column_dimensions[stulpelis].width = plotis
    buferis = io.BytesIO()
    knyga.save(buferis)
    return buferis.getvalue()
