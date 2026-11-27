"""Įvykiai ir įvykių skirstytuvas (aprašo 6 pav. klasė IvykiuSkirstytuvas).

Maršrutai ir kiti moduliai apie įvykį praneša vienu kvietimu, pvz.:

    skelbti("skelbimas_paskelbtas", skelbimas)

Skirstytuvas per taisyklių variklį randa aktyvias taisykles, kiekvienam gavėjui
per šablonų apdorotoją suformuoja tekstą ir įrašo pranešimus į eilę. Įrašai
išsaugomi toje pačioje transakcijoje kaip ir pats įvykis: jei skelbimo išsaugoti
nepavyksta, neatsiranda ir pranešimų (aprašo 8 pav.).
"""
import logging
from dataclasses import dataclass

from flask import current_app
from werkzeug.routing import BuildError

from models import PranesimuNustatymas, db
from services.eile import PranesimuEile
from services.sablonai import SablonoKlaida, SablonuApdorotojas
from services.taisykles import TaisykliuVariklis

zurnalas = logging.getLogger("ivykiai")

TEVAS, MOKYTOJAS, ADMINISTRATORIUS = "tevas", "mokytojas", "administratorius"
VISI = frozenset({TEVAS, MOKYTOJAS, ADMINISTRATORIUS})
DARBUOTOJAI = frozenset({MOKYTOJAS, ADMINISTRATORIUS})
TIK_ADMIN = frozenset({ADMINISTRATORIUS})
TIK_TEVAI = frozenset({TEVAS})


@dataclass(frozen=True)
class IvykioTipas:
    """Įvykio tipo aprašas (FR-A02)."""
    kodas: str
    pavadinimas: str
    objekto_tipas: str           # kokio objekto duomenys perduodami šablonui
    gavejai: tuple               # leistinos gavėjų grupės (services/taisykles.py)
    kam: frozenset = frozenset()  # kurioms rolėms rodomas naudotojo nustatymuose (FR-A07)
    priminimas: bool = False     # priminimas: siunčiamas likus poslinkis_d dienų iki datos
    darbo_dienomis: bool = False  # poslinkis skaičiuojamas darbo dienomis
    privalomas: bool = False     # el. laiškas siunčiamas nepaisant naudotojo nustatymų


_VIESI = ("tevai", "darbuotojai", "visi")

IVYKIU_TIPAI = {t.kodas: t for t in (
    IvykioTipas("skelbimas_paskelbtas", "Paskelbtas skelbimas", "skelbimas", _VIESI, VISI),
    IvykioTipas("renginys_sukurtas", "Sukurtas renginys", "renginys", _VIESI, VISI),
    IvykioTipas("renginys_pakeistas", "Pakeistas renginys", "renginys", _VIESI, VISI),
    IvykioTipas("renginys_atsauktas", "Atšauktas renginys", "renginys", _VIESI, VISI),
    IvykioTipas("renginys_artejantis", "Artėjantis renginys", "renginys", _VIESI, VISI,
                priminimas=True),
    IvykioTipas("vgk_atvejis_uzregistruotas", "Užregistruotas kreipimasis į komisiją", "vgk_atvejis",
                ("vgk_pirmininkas", "vgk_nariai"), DARBUOTOJAI),
    IvykioTipas("vgk_posedis_suplanuotas", "Suplanuotas komisijos posėdis", "vgk_posedis",
                ("posedzio_dalyviai", "vgk_nariai"), VISI, privalomas=True),
    IvykioTipas("vgk_posedis_atsauktas", "Atšauktas komisijos posėdis", "vgk_posedis",
                ("posedzio_dalyviai", "vgk_nariai"), VISI, privalomas=True),
    IvykioTipas("vgk_posedis_artejantis", "Artėjantis komisijos posėdis", "vgk_posedis",
                ("posedzio_dalyviai",), VISI, priminimas=True, darbo_dienomis=True, privalomas=True),
    # FR-V04: skubų posėdį (mažiau nei 5 darbo dienos) tvirtina administratorius
    IvykioTipas("vgk_posedis_laukia_patvirtinimo", "Skubus posėdis laukia patvirtinimo", "vgk_posedis",
                ("administratoriai",), TIK_ADMIN, privalomas=True),
    IvykioTipas("vgk_posedis_atmestas", "Nepatvirtintas skubus posėdis", "vgk_posedis",
                ("vgk_valdytojai", "vgk_pirmininkas"), DARBUOTOJAI),
    IvykioTipas("priemones_terminas_artejantis", "Artėja priemonės terminas", "vgk_priemone",
                ("atsakingas",), DARBUOTOJAI, priminimas=True, darbo_dienomis=True),
    IvykioTipas("priemone_veluoja", "Vėluojanti priemonė", "vgk_priemone",
                ("vgk_pirmininkas", "atsakingas"), DARBUOTOJAI),
    IvykioTipas("pazymos_prasymas_pateiktas", "Pateiktas pažymos prašymas", "pazymos_prasymas",
                ("administratoriai",), TIK_ADMIN),
    IvykioTipas("pazymos_prasymas_ivykdytas", "Įvykdytas pažymos prašymas", "pazymos_prasymas",
                ("prasymo_teikejas",), TIK_TEVAI),
    IvykioTipas("pazymos_prasymas_atmestas", "Atmestas pažymos prašymas", "pazymos_prasymas",
                ("prasymo_teikejas",), TIK_TEVAI),
    IvykioTipas("importas_baigtas", "Baigtas duomenų importas", "importo_sesija",
                ("iniciatorius", "administratoriai"), TIK_ADMIN),
    IvykioTipas("tevo_paskyra_sukurta", "Sukurta tėvo paskyra", "naudotojas",
                ("naujas_naudotojas",), privalomas=True),
    IvykioTipas("menesio_suvestine", "Mėnesio suvestinė", "suvestine",
                ("administratoriai",), TIK_ADMIN),
)}

PRIMINIMU_TIPAI = tuple(kodas for kodas, tipas in IVYKIU_TIPAI.items() if tipas.priminimas)


def rodomas_nustatymuose(tipas, naudotojas):
    """Ar įvykio tipas rodomas naudotojo pranešimų nustatymuose (FR-A07)."""
    if naudotojas.role not in tipas.kam:
        return False
    if naudotojas.role == MOKYTOJAS and tipas.objekto_tipas in ("vgk_atvejis", "vgk_posedis"):
        return naudotojas.yra_vgk_narys
    return True


# --- Nuorodos į sistemą -----------------------------------------------------

def kelias(endpoint, **reiksmes):
    """Santykinis kelias, pvz., „/kalendorius/5“. Veikia ir fono procese (be HTTP užklausos).

    Jei puslapio dar nėra (modulis kuriamas vėliau), grąžinamas pradžios puslapis.
    """
    try:
        return current_app.url_map.bind("").build(endpoint, reiksmes)
    except BuildError:
        return "/"


def nuoroda(endpoint, **reiksmes):
    """Pilna nuoroda el. laiškui, pvz., „http://127.0.0.1:5000/kalendorius/5“."""
    adresas = current_app.config.get("SISTEMOS_ADRESAS", "http://127.0.0.1:5000").rstrip("/")
    return adresas + kelias(endpoint, **reiksmes)


# --- Šablonų duomenys -----------------------------------------------------------
# Šablonui perduodami tik čia išvardyti laukai (ne duomenų bazės objektai), todėl
# per šabloną negalima pasiekti kitų duomenų (NFR-07). VGK duomenyse nėra mokinio
# vardo ir svarstymo priežasties – el. laiške tik data, laikas, vieta ir nuoroda (NFR-10).

def _data(reiksme):
    return reiksme.strftime("%Y-%m-%d") if reiksme else ""


def _laikas(reiksme):
    return reiksme.strftime("%H:%M") if reiksme else ""


def _skelbimas(s, gavejas):
    tikslas = ("parents.skelbimai", {}) if gavejas.yra_tevas else \
        ("announcements.perziureti", {"skelbimo_id": s.id})
    return {"skelbimas": {
        "pavadinimas": s.pavadinimas,
        "turinys": s.turinys,
        "kategorija": s.kategorija,
        "svarbus": bool(s.svarbus),
        "data": _data(s.sukurtas),
    }}, tikslas


def _renginys(r, gavejas):
    return {"renginys": {
        "pavadinimas": r.pavadinimas,
        "aprasymas": r.aprasymas or "",
        "data": _data(r.pradzios_data),
        "laikas": _laikas(r.pradzios_laikas),
        "vieta": r.vieta or "",
        "kategorija": r.kategorija,
    }}, ("calendar.perziureti", {"renginio_id": r.id})


def _posedis(p, gavejas):
    # Posėdžio puslapį mato tik komisijos nariai; tėvams ir kitiems – nuoroda į jų pradžios puslapį
    if gavejas.gali_matyti_vgk:
        tikslas = ("vgk.posedis", {"posedzio_id": p.id})
    else:
        tikslas = ("parents.dashboard", {}) if gavejas.yra_tevas else ("dashboard.index", {})
    return {"posedis": {"data": _data(p.data), "laikas": _laikas(p.laikas), "vieta": p.vieta}}, tikslas


def _atvejis(a, gavejas):
    return {"atvejis": {"numeris": a.numeris, "data": _data(a.sukurta)}}, ("vgk.atvejis", {"atvejo_id": a.id})


def _priemone(p, gavejas):
    return {"priemone": {"terminas": _data(p.terminas)}}, ("vgk.mano_priemones", {})


def _prasymas(p, gavejas):
    tikslas = ("dokumentai.mano_pazymos", {}) if gavejas.yra_tevas else ("dokumentai.prasymai", {})
    return {"prasymas": {
        "paskirtis": p.paskirtis,
        "busena": p.busenos_pavadinimas,
        "mokinys": p.mokinys.pilnas_vardas if p.mokinys else "",
        "numeris": p.dokumentas.numeris if p.dokumentas else "",
        "priezastis": p.atmetimo_priezastis or "",
    }}, tikslas


def _importas(s, gavejas):
    return {"importas": {
        "failo_vardas": s.failo_vardas,
        "eiluciu_sk": s.eiluciu_sk,
        "tinkamu_sk": s.tinkamu_sk,
        "klaidu_sk": s.klaidu_sk,
    }}, ("importas.ataskaita", {"sesijos_id": s.id})


def _paskyra(naudotojas, gavejas):
    # Kvietime – vienkartinė nuoroda slaptažodžiui susikurti (slaptažodis laišku nesiunčiamas)
    from services.paskyros import slaptazodzio_zetonas
    return {"paskyra": {"el_pastas": naudotojas.email}},         ("auth.nustatyti_slaptazodi", {"zetonas": slaptazodzio_zetonas(naudotojas)})


def _suvestine(dokumentas, gavejas):
    return {"suvestine": {
        "numeris": dokumentas.numeris,
        "laikotarpis": getattr(dokumentas, "laikotarpis", ""),
    }}, ("dokumentai.registras", {})


_OBJEKTU_DUOMENYS = {
    "skelbimas": _skelbimas,
    "renginys": _renginys,
    "vgk_posedis": _posedis,
    "vgk_atvejis": _atvejis,
    "vgk_priemone": _priemone,
    "pazymos_prasymas": _prasymas,
    "importo_sesija": _importas,
    "naudotojas": _paskyra,
    "suvestine": _suvestine,
}


def sukurti_konteksta(ivykis, objektas, gavejas):
    """Šablono kintamieji vienam gavėjui."""
    duomenys, (endpoint, reiksmes) = _OBJEKTU_DUOMENYS[ivykis.objekto_tipas](objektas, gavejas)
    duomenys.update({
        "gavejas": {"vardas": gavejas.vardas, "pavarde": gavejas.pavarde,
                    "pilnas_vardas": gavejas.pilnas_vardas},
        "mokykla": {"pavadinimas": current_app.config.get("MOKYKLOS_PAVADINIMAS", "")},
        "nuoroda": nuoroda(endpoint, **reiksmes),
    })
    return duomenys


# --- Unikalus raktas ------------------------------------------------------------

def objekto_raktas(objekto_tipas, objekto_id):
    """Rakto pradžia, pagal kurią atšaukiami objekto pranešimai, pvz., „renginys-15“."""
    return f"{objekto_tipas}-{objekto_id}"


def unikalus_raktas(ivykis, objektas, taisykle, gavejas, kanalas, papildomas=None):
    """Pvz.: renginys-15/renginys_artejantis/t2/g7/el_pastas/2026-12-18.

    Raktą sudaro objekto, įvykio, taisyklės, gavėjo ir kanalo identifikatoriai, todėl
    tas pats pranešimas tam pačiam gavėjui sukuriamas tik kartą (FR-A04). Papildoma
    dalis atskiria, pvz., priminimus skirtingoms datoms ar kelis to paties renginio pakeitimus.
    """
    dalys = [objekto_raktas(ivykis.objekto_tipas, objektas.id), ivykis.kodas,
             f"t{taisykle.id}", f"g{gavejas.id}", kanalas]
    if papildomas:
        dalys.append(str(papildomas))
    return "/".join(dalys)[:200]


# --- Skirstytuvas -------------------------------------------------------------------

class IvykiuSkirstytuvas:
    """Vienintelis įėjimo taškas įvykiams: įvykis -> taisyklės -> pranešimų eilė."""

    def __init__(self, variklis=None, apdorotojas=None, eile=None):
        self.variklis = variklis or TaisykliuVariklis()
        self.apdorotojas = apdorotojas or SablonuApdorotojas()
        self.eile = eile or PranesimuEile()

    def skelbti(self, tipas, objektas, papildomas_raktas=None, taisykles=None):
        """Sukuria pranešimus eilėje ir grąžina jų skaičių. Įrašų neišsaugo (commit)."""
        ivykis = IVYKIU_TIPAI.get(tipas)
        if ivykis is None:
            raise ValueError(f"Nežinomas įvykio tipas: {tipas}")
        if getattr(objektas, "id", None) is None:
            db.session.flush()  # naujam objektui reikia id rakto sudarymui

        if taisykles is None:
            taisykles = self.variklis.rasti_taisykles(tipas)

        sukurta = 0
        for taisykle in taisykles:
            if not self.variklis.tenkina_salyga(taisykle, objektas):
                continue
            gavejai = self.variklis.nustatyti_gavejus(taisykle, objektas)
            atsisake = self._atsisake_el_laisku(ivykis, gavejai)
            for gavejas in gavejai:
                try:
                    tema, tekstas = self.apdorotojas.formuoti(
                        taisykle.sablonas, sukurti_konteksta(ivykis, objektas, gavejas))
                except SablonoKlaida as klaida:
                    # Ta pati klaida kartotųsi kiekvienam gavėjui – taisyklė praleidžiama
                    zurnalas.error("Taisyklės „%s“ šablono klaida: %s", taisykle.pavadinimas, klaida)
                    break
                for kanalas in taisykle.kanalu_sarasas:
                    if kanalas == "el_pastas" and gavejas.id in atsisake:
                        continue  # FR-A07: naudotojas el. laiškų apie šį įvykį negauna
                    raktas = unikalus_raktas(ivykis, objektas, taisykle, gavejas, kanalas, papildomas_raktas)
                    if self.eile.prideti(gavejas, kanalas, raktas, tema, tekstas, taisykle=taisykle):
                        sukurta += 1
        return sukurta

    @staticmethod
    def _atsisake_el_laisku(ivykis, gavejai):
        """Gavėjų id, kurie nustatymuose išjungė el. laiškus apie šį įvykį."""
        if ivykis.privalomas or not gavejai:
            return set()
        eilutes = PranesimuNustatymas.query.filter(
            PranesimuNustatymas.ivykio_tipas == ivykis.kodas,
            PranesimuNustatymas.vartotojo_id.in_([g.id for g in gavejai]),
            PranesimuNustatymas.el_pastas.is_(False),
        )
        return {n.vartotojo_id for n in eilutes}


def skelbti(tipas, objektas, **parametrai):
    """Patogi funkcija maršrutams: skelbti("renginys_sukurtas", renginys)."""
    return IvykiuSkirstytuvas().skelbti(tipas, objektas, **parametrai)


def atsaukti_pranesimus(objekto_tipas, objekto_id):
    """FR-A08: atšaukti dar neišsiųstus pranešimus apie objektą."""
    return PranesimuEile().atsaukti_objekto(objekto_raktas(objekto_tipas, objekto_id))
