"""Pažymų prašymai, laikotarpio ataskaitos ir dokumentų prieiga (FR-D01–FR-D08).

Prašymo kelias: tėvas pateikia (Pateiktas) -> administratorius patvirtina (sugeneruojama
pažyma, Įvykdytas) arba atmeta nurodydamas priežastį (Atmestas). Apie kiekvieną žingsnį
pranešama per automatizavimo posistemį toje pačioje transakcijoje.
"""
from datetime import date, datetime, time, timedelta

from models import (
    Dokumentas,
    EilesIrasas,
    Klase,
    PazymosPrasymas,
    VgkAtvejis,
    VgkPosedis,
    VgkPriemone,
    db,
    utc_dabar,
)
from services.dokumentai import AtaskaitosGeneratorius, PazymosGeneratorius
from services.ivykiai import skelbti

# Pažymos paskirtys formoje (aprašo 16 pav. maketas)
PASKIRTYS = (
    "Pateikti „Sodrai“",
    "Būrelio lankymui",
    "Darbdaviui",
    "Socialinės paramos skyriui",
    "Kita",
)
MENESIAI = ("sausis", "vasaris", "kovas", "balandis", "gegužė", "birželis", "liepa",
            "rugpjūtis", "rugsėjis", "spalis", "lapkritis", "gruodis")


class PrasymoKlaida(Exception):
    """Netinkamas veiksmas su prašymu (pvz., jis jau išnagrinėtas)."""


def _uzrakinti_prasyma(prasymas):
    """Užrakina prašymo eilutę: du administratoriai negali vienu metu jo patvirtinti du kartus."""
    return db.session.execute(
        db.select(PazymosPrasymas).where(PazymosPrasymas.id == prasymas.id).with_for_update()
    ).scalar_one()


def pateikti_prasyma(tevas, mokinys, paskirtis, papildoma=""):
    """FR-D01: tėvas užsako pažymą apie savo vaiką."""
    if mokinys is None or tevas.vaikai.filter_by(id=mokinys.id).first() is None:
        raise PrasymoKlaida("Pažymą galima užsakyti tik apie savo vaiką.")
    paskirtis = (paskirtis or "").strip()
    if not paskirtis:
        raise PrasymoKlaida("Nurodykite pažymos paskirtį.")
    if papildoma and papildoma.strip():
        paskirtis = f"{paskirtis} ({papildoma.strip()})"

    prasymas = PazymosPrasymas(tevo_id=tevas.id, mokinio_id=mokinys.id, paskirtis=paskirtis[:200])
    db.session.add(prasymas)
    skelbti("pazymos_prasymas_pateiktas", prasymas)  # pranešimas administratoriui
    db.session.commit()
    return prasymas


def patvirtinti_prasyma(prasymas, administratorius):
    """FR-D02, FR-D03: patvirtinus sugeneruojama PDF pažyma su numeriu ir pranešama tėvui."""
    prasymas = _uzrakinti_prasyma(prasymas)
    if prasymas.busena != PazymosPrasymas.PATEIKTAS:
        raise PrasymoKlaida("Šis prašymas jau išnagrinėtas.")

    dokumentas = PazymosGeneratorius().parengti(
        {"mokinys": prasymas.mokinys, "paskirtis": prasymas.paskirtis},
        mokinys=prasymas.mokinys, sukure=administratorius,
    )
    prasymas.dokumentas = dokumentas
    prasymas.busena = PazymosPrasymas.IVYKDYTAS
    prasymas.nagrinejo_id = administratorius.id
    skelbti("pazymos_prasymas_ivykdytas", prasymas)
    db.session.commit()
    return dokumentas


def atmesti_prasyma(prasymas, administratorius, priezastis):
    """FR-D02: atmetant būtina nurodyti priežastį – ji parodoma tėvui."""
    priezastis = (priezastis or "").strip()
    if not priezastis:
        raise PrasymoKlaida("Nurodykite atmetimo priežastį.")
    prasymas = _uzrakinti_prasyma(prasymas)
    if prasymas.busena != PazymosPrasymas.PATEIKTAS:
        raise PrasymoKlaida("Šis prašymas jau išnagrinėtas.")

    prasymas.busena = PazymosPrasymas.ATMESTAS
    prasymas.atmetimo_priezastis = priezastis
    prasymas.nagrinejo_id = administratorius.id
    skelbti("pazymos_prasymas_atmestas", prasymas)
    db.session.commit()
    return prasymas


def gali_atsisiusti(naudotojas, dokumentas):
    """Kas gali atsisiųsti dokumentą: administratorius – visus; tėvas – savo vaiko pažymas;
    VGK narys – posėdžių protokolus (NFR-06)."""
    if naudotojas.yra_administratorius:
        return True
    if dokumentas.tipas == "PZ" and naudotojas.yra_tevas and dokumentas.mokinio_id:
        return naudotojas.vaikai.filter_by(id=dokumentas.mokinio_id).first() is not None
    if dokumentas.tipas == "PR":
        return naudotojas.yra_vgk_narys
    return False


# --- Ataskaitos (FR-D06, FR-D07) ------------------------------------------------------

def _laiko_ribos(nuo, iki):
    """Datos -> [nuo 00:00; iki+1 00:00) laiko žymos palyginimui su UTC laukais."""
    return datetime.combine(nuo, time.min), datetime.combine(iki + timedelta(days=1), time.min)


def ataskaitos_duomenys(nuo, iki):
    """Laikotarpio suvestinės skaičiai: mokiniai, VGK, priemonės, pranešimai, dokumentai."""
    pradzia, pabaiga = _laiko_ribos(nuo, iki)
    klases = [(k.pavadinimas, len(k.mokiniai)) for k in Klase.query.order_by(Klase.pavadinimas)]
    priemones = VgkPriemone.query.filter(VgkPriemone.terminas.between(nuo, iki))
    issiusta = EilesIrasas.query.filter(EilesIrasas.busena == EilesIrasas.ISSIUSTAS,
                                        EilesIrasas.issiusta >= pradzia, EilesIrasas.issiusta < pabaiga)
    return {
        "klases": klases,
        "mokiniu_is_viso": sum(kiekis for _, kiekis in klases),
        "vgk_nauji": VgkAtvejis.query.filter(VgkAtvejis.sukurta >= pradzia, VgkAtvejis.sukurta < pabaiga).count(),
        "vgk_posedziai": VgkPosedis.query.filter(VgkPosedis.busena == VgkPosedis.IVYKES,
                                                 VgkPosedis.data.between(nuo, iki)).count(),
        "vgk_aktyvus": VgkAtvejis.query.filter(VgkAtvejis.busena != VgkAtvejis.UZBAIGTAS).count(),
        "priemones_is_viso": priemones.count(),
        "priemones_ivykdyta": priemones.filter(VgkPriemone.busena == VgkPriemone.IVYKDYTA).count(),
        "priemones_veluoja": priemones.filter(VgkPriemone.busena == VgkPriemone.VELUOJA).count(),
        "issiusta_el_pastu": issiusta.filter(EilesIrasas.kanalas == "el_pastas").count(),
        "issiusta_sistemoje": issiusta.filter(EilesIrasas.kanalas == "sistema").count(),
        "nepavyko": EilesIrasas.query.filter(EilesIrasas.busena == EilesIrasas.NEPAVYKO,
                                             EilesIrasas.siusti_po >= pradzia,
                                             EilesIrasas.siusti_po < pabaiga).count(),
        "pazymu": Dokumentas.query.filter(Dokumentas.tipas == "PZ", Dokumentas.sukurta >= pradzia,
                                          Dokumentas.sukurta < pabaiga).count(),
    }


def parengti_ataskaita(nuo, iki, sukure=None):
    """FR-D07: ataskaita už pasirinktą laikotarpį (PDF dokumentų registre)."""
    if iki < nuo:
        raise PrasymoKlaida("Laikotarpio pabaiga negali būti ankstesnė už pradžią.")
    dokumentas = AtaskaitosGeneratorius().parengti(
        {"nuo": nuo, "iki": iki, "statistika": ataskaitos_duomenys(nuo, iki)}, sukure=sukure)
    db.session.commit()
    return dokumentas


def ankstesnis_menuo(siandien):
    """Praėjusio mėnesio pirma ir paskutinė diena."""
    iki = siandien.replace(day=1) - timedelta(days=1)
    return iki.replace(day=1), iki


def laikotarpio_pavadinimas(nuo):
    return f"{nuo.year} m. {MENESIAI[nuo.month - 1]}"


def sukurti_menesio_suvestine(siandien=None):
    """FR-D06: kiekvieno mėnesio 1 d. fono procesas parengia praėjusio mėnesio suvestinę
    ir apie ją praneša administratoriui (pagal taisyklę „Mėnesio suvestinė“)."""
    siandien = siandien or date.today()
    # Jei fono procesas buvo perkrautas, tą pačią dieną antra suvestinė nekuriama
    siandienos_pradzia = datetime.combine(utc_dabar().date(), time.min)
    if Dokumentas.query.filter(Dokumentas.tipas == "AT", Dokumentas.sukure_id.is_(None),
                               Dokumentas.sukurta >= siandienos_pradzia).first():
        return None

    nuo, iki = ankstesnis_menuo(siandien)
    dokumentas = parengti_ataskaita(nuo, iki)
    dokumentas.laikotarpis = laikotarpio_pavadinimas(nuo)  # tik šablonui, stulpelyje nesaugoma
    skelbti("menesio_suvestine", dokumentas)
    db.session.commit()
    return dokumentas
