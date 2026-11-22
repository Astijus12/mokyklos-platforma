"""Vaiko gerovės komisijos (VGK) logika (FR-V01–FR-V11).

Atvejo būsenos (aprašo 3 pav.): Užregistruotas -> Svarstomas (įtrauktas į
patvirtintą posėdį) -> Taikomos priemonės (posėdyje paskirtos priemonės) ->
Užbaigtas (įvykdžius visas priemones arba priėmus nutarimą be priemonių).
Atšaukus posėdį atvejis grįžta į „Užregistruotas“, užbaigtą atvejį galima atnaujinti.

Visi būsenų perėjimai aprašyti tik čia – maršrutai būsenų tiesiogiai nekeičia.
Apie posėdžius ir priemones pranešama per automatizavimo posistemį.
"""
from datetime import date

from models import (
    User,
    VgkAtvejis,
    VgkDalyvis,
    VgkPosedis,
    VgkPriemone,
    VgkSvarstymas,
    db,
    utc_dabar,
)
from services.dokumentai import ProtokoloGeneratorius
from services.ivykiai import atsaukti_pranesimus, skelbti
from services.kalendorius import darbo_dienos_iki, data_is_formos, laikas_is_formos  # noqa: F401 (naudoja routes/vgk.py)

# Kvietimai siunčiami ne vėliau kaip prieš 5 darbo dienas (ŠMSM 2024-07-19 įsak. Nr. V-818)
MIN_DARBO_DIENU = 5


class VgkKlaida(Exception):
    """Neleistinas veiksmas (pvz., per trumpas terminas be skubos priežasties)."""


# --- Kreipimasis (FR-V01) -------------------------------------------------------------

def pateikti_kreipimasi(mokytojas, mokinys, priezastis):
    """Mokytojas pateikia kreipimąsi – atvejis „Užregistruotas“, pirmininkui pranešama."""
    priezastis = (priezastis or "").strip()
    if mokinys is None:
        raise VgkKlaida("Pasirinkite mokinį.")
    if len(priezastis) < 10:
        raise VgkKlaida("Aprašykite kreipimosi priežastį (bent 10 simbolių).")
    atvejis = VgkAtvejis(mokinio_id=mokinys.id, pateike_id=mokytojas.id, priezastis=priezastis,
                         busena=VgkAtvejis.UZREGISTRUOTAS, sukurta=utc_dabar())
    db.session.add(atvejis)
    skelbti("vgk_atvejis_uzregistruotas", atvejis)
    db.session.commit()
    return atvejis


# --- Posėdžio planavimas (FR-V03, FR-V04, FR-V05) ------------------------------------

def darbo_dienu_iki_posedzio(data, siandien=None):
    return darbo_dienos_iki(data, siandien or date.today())


def galimi_darbotvarkei():
    """Atvejai, kuriuos galima įtraukti į posėdį: visi, išskyrus užbaigtus."""
    return (VgkAtvejis.query.filter(VgkAtvejis.busena != VgkAtvejis.UZBAIGTAS)
            .order_by(VgkAtvejis.sukurta).all())


def _vaidmuo(naudotojas):
    return naudotojas.vgk_pareigos if naudotojas.yra_vgk_narys else "narys"


def dalyviu_grupes(atvejai):
    """Siūlomi dalyviai pagal darbotvarkę (maketas 13): komisijos nariai, kiekvieno mokinio
    tėvai ir mokinių klasių vadovai. Grąžina [(kodas, pavadinimas, [(naudotojas, vaidmuo)])]."""
    nariai = User.query.filter(User.vgk_pareigos.isnot(None)).order_by(User.pavarde).all()
    grupes = [("nariai", f"Komisijos nariai ({len(nariai)})", [(n, _vaidmuo(n)) for n in nariai])]
    for atvejis in atvejai:
        tevai = list(atvejis.mokinys.tevai)
        grupes.append((f"tevai_{atvejis.id}", f"{atvejis.mokinys.pilnas_vardas}: tėvai ({len(tevai)})",
                       [(t, "tevas") for t in tevai]))
    vadovai = {a.mokinys.klase.vadovas.id: a.mokinys.klase.vadovas
               for a in atvejai if a.mokinys.klase and a.mokinys.klase.vadovas}
    grupes.append(("vadovai", f"Klasių vadovai ({len(vadovai)})",
                   [(v, "klases_vadovas") for v in vadovai.values()]))
    return grupes


def issaugoti_posedi(posedis, data, laikas, vieta, atvejai, pazymetos_grupes, kviestiniai="",
                     skubos_priezastis="", patvirtinti=False, siandien=None):
    """Išsaugo posėdžio juodraštį arba jį patvirtina ir išsiunčia kvietimus.

    Patvirtinant tikrinama: bent vienas atvejis ir ne mažiau kaip 5 darbo dienos
    iki posėdžio; jei mažiau – būtina skubos priežastis (FR-V04).
    """
    siandien = siandien or date.today()
    if posedis is not None and posedis.busena != VgkPosedis.JUODRASTIS:
        raise VgkKlaida("Redaguoti galima tik posėdžio juodraštį.")
    if data is None or laikas is None or not (vieta or "").strip():
        raise VgkKlaida("Nurodykite posėdžio datą, laiką ir vietą.")
    if data < siandien:
        raise VgkKlaida("Posėdžio data negali būti praėjusi.")
    if any(a.busena == VgkAtvejis.UZBAIGTAS for a in atvejai):
        raise VgkKlaida("Užbaigto atvejo įtraukti negalima – pirmiausia jį atnaujinkite.")
    skubos_priezastis = (skubos_priezastis or "").strip()
    if patvirtinti:
        if not atvejai:
            raise VgkKlaida("Į darbotvarkę įtraukite bent vieną atvejį.")
        if darbo_dienu_iki_posedzio(data, siandien) < MIN_DARBO_DIENU and not skubos_priezastis:
            raise VgkKlaida(f"Iki posėdžio liko mažiau nei {MIN_DARBO_DIENU} darbo dienos – "
                            "pasirinkite vėlesnę datą arba nurodykite skubos priežastį.")

    if posedis is None:
        posedis = VgkPosedis(busena=VgkPosedis.JUODRASTIS)
        db.session.add(posedis)
    posedis.data, posedis.laikas, posedis.vieta = data, laikas, vieta.strip()
    posedis.skubos_priezastis = skubos_priezastis or None

    # Darbotvarkė: svarstymai sudaromi iš naujo pagal pasirinktą eilę
    posedis.svarstymai.clear()
    db.session.flush()
    for eiles_nr, atvejis in enumerate(atvejai, start=1):
        posedis.svarstymai.append(VgkSvarstymas(atvejis=atvejis, eiles_nr=eiles_nr))

    # Dalyviai: pažymėtos grupės (be pasikartojimų) ir kviestiniai asmenys be paskyros
    posedis.dalyviai.clear()
    jau_itraukti = set()
    for kodas, _, nariai in dalyviu_grupes(atvejai):
        if kodas not in pazymetos_grupes:
            continue
        for naudotojas, vaidmuo in nariai:
            if naudotojas.id not in jau_itraukti:
                jau_itraukti.add(naudotojas.id)
                posedis.dalyviai.append(VgkDalyvis(vartotojo_id=naudotojas.id,
                                                   vardas_pavarde=naudotojas.pilnas_vardas, vaidmuo=vaidmuo))
    for eilute in (kviestiniai or "").splitlines():
        if eilute.strip():
            posedis.dalyviai.append(VgkDalyvis(vardas_pavarde=eilute.strip()[:160], vaidmuo="kviestinis"))

    if patvirtinti:
        posedis.busena = VgkPosedis.SUPLANUOTAS
        for atvejis in atvejai:
            if atvejis.busena == VgkAtvejis.UZREGISTRUOTAS:
                atvejis.busena = VgkAtvejis.SVARSTOMAS
        db.session.flush()
        skelbti("vgk_posedis_suplanuotas", posedis)  # kvietimai nariams ir tėvams (FR-V05)
    db.session.commit()
    return posedis


def atsaukti_posedi(posedis):
    """Atšaukia posėdį: neišsiųsti kvietimai atšaukiami (FR-A08), dalyviams pranešama,
    atvejai, kurie buvo svarstomi tik šiame posėdyje, grįžta į „Užregistruotas“."""
    if posedis.busena not in (VgkPosedis.JUODRASTIS, VgkPosedis.SUPLANUOTAS):
        raise VgkKlaida("Įvykusio ar jau atšaukto posėdžio atšaukti negalima.")
    buvo_suplanuotas = posedis.busena == VgkPosedis.SUPLANUOTAS
    posedis.busena = VgkPosedis.ATSAUKTAS
    for svarstymas in posedis.svarstymai:
        atvejis = svarstymas.atvejis
        kiti = [s for s in atvejis.svarstymai
                if s.posedis is not posedis and s.posedis.busena != VgkPosedis.ATSAUKTAS]
        if atvejis.busena == VgkAtvejis.SVARSTOMAS and not kiti:
            atvejis.busena = VgkAtvejis.UZREGISTRUOTAS
    atsaukti_pranesimus("vgk_posedis", posedis.id)
    if buvo_suplanuotas:
        skelbti("vgk_posedis_atsauktas", posedis)
    db.session.commit()
    return posedis


# --- Posėdžio eiga ir protokolas (FR-V06, FR-V07) -------------------------------------

def irasyti_posedzio_duomenis(posedis, dalyvavo_ids, pasizadejimas_ids, nutarimai):
    """Sekretorius pažymi dalyvius ir įrašo kiekvieno atvejo nutarimą."""
    if posedis.busena not in (VgkPosedis.SUPLANUOTAS, VgkPosedis.IVYKES):
        raise VgkKlaida("Duomenis galima įrašyti tik patvirtintam posėdžiui.")
    for dalyvis in posedis.dalyviai:
        dalyvis.dalyvavo = dalyvis.id in dalyvavo_ids
        dalyvis.pasizadejimas = dalyvis.id in pasizadejimas_ids
    for svarstymas in posedis.svarstymai:
        if svarstymas.id in nutarimai:
            svarstymas.nutarimas = (nutarimai[svarstymas.id] or "").strip() or None
    db.session.commit()


def prideti_priemone(svarstymas, aprasymas, atsakingas, terminas):
    """Paskiria priemonę (atsakingas asmuo ir terminas); atvejis tampa „Taikomos priemonės“."""
    aprasymas = (aprasymas or "").strip()
    if not aprasymas or atsakingas is None or terminas is None:
        raise VgkKlaida("Nurodykite priemonę, atsakingą asmenį ir terminą.")
    if svarstymas.posedis.busena not in (VgkPosedis.SUPLANUOTAS, VgkPosedis.IVYKES):
        raise VgkKlaida("Priemones galima skirti tik patvirtintame posėdyje.")
    priemone = VgkPriemone(aprasymas=aprasymas, atsakingo_id=atsakingas.id, terminas=terminas)
    svarstymas.priemones.append(priemone)
    if svarstymas.atvejis.busena in (VgkAtvejis.UZREGISTRUOTAS, VgkAtvejis.SVARSTOMAS):
        svarstymas.atvejis.busena = VgkAtvejis.TAIKOMOS_PRIEMONES
    db.session.commit()
    return priemone


def uzbaigti_posedi(posedis, naudotojas):
    """Posėdis pažymimas įvykusiu ir sugeneruojamas protokolo projektas (PDF su numeriu)."""
    if posedis.busena != VgkPosedis.SUPLANUOTAS:
        raise VgkKlaida("Užbaigti galima tik suplanuotą posėdį.")
    if not any(d.dalyvavo for d in posedis.dalyviai):
        raise VgkKlaida("Prieš užbaigiant pažymėkite posėdžio dalyvius.")
    posedis.busena = VgkPosedis.IVYKES
    db.session.flush()
    posedis.protokolas = ProtokoloGeneratorius().parengti({"posedis": posedis}, sukure=naudotojas)
    db.session.commit()
    return posedis.protokolas


# --- Priemonės ir atvejo užbaigimas (FR-V08–FR-V10) ----------------------------------

def gali_pazymeti_priemone(naudotojas, priemone):
    return (priemone.atsakingo_id == naudotojas.id or naudotojas.yra_administratorius
            or naudotojas.gali_planuoti_vgk_posedzius)


def pazymeti_ivykdyta(priemone, naudotojas, rezultatas):
    if not gali_pazymeti_priemone(naudotojas, priemone):
        raise VgkKlaida("Pažymėti priemonę gali tik atsakingas asmuo arba komisijos pirmininkas, sekretorius.")
    if priemone.busena == VgkPriemone.IVYKDYTA:
        raise VgkKlaida("Priemonė jau pažymėta įvykdyta.")
    priemone.busena = VgkPriemone.IVYKDYTA
    priemone.rezultatas = (rezultatas or "").strip() or None
    db.session.commit()
    return priemone


def gali_uzbaigti(atvejis):
    """Atvejį galima užbaigti, kai priimtas nutarimas ir visos priemonės įvykdytos."""
    if atvejis.busena == VgkAtvejis.UZBAIGTAS:
        return False
    if not any(s.nutarimas for s in atvejis.svarstymai):
        return False
    return all(p.busena == VgkPriemone.IVYKDYTA for s in atvejis.svarstymai for p in s.priemones)


def uzbaigti_atveji(atvejis):
    if not gali_uzbaigti(atvejis):
        raise VgkKlaida("Atvejį galima užbaigti tik priėmus nutarimą ir įvykdžius visas priemones.")
    atvejis.busena = VgkAtvejis.UZBAIGTAS
    atvejis.uzbaigta = utc_dabar()
    db.session.commit()


def atnaujinti_atveji(atvejis):
    """Užbaigtas atvejis atnaujinamas ir vėl laukia svarstymo."""
    if atvejis.busena != VgkAtvejis.UZBAIGTAS:
        raise VgkKlaida("Atnaujinti galima tik užbaigtą atvejį.")
    atvejis.busena = VgkAtvejis.UZREGISTRUOTAS
    atvejis.uzbaigta = None
    db.session.commit()


def pazymeti_veluojancias(siandien=None):
    """FR-V09: praėjus terminui priemonė pažymima vėluojančia ir pranešama pirmininkui."""
    siandien = siandien or date.today()
    veluojancios = VgkPriemone.query.filter(VgkPriemone.busena == VgkPriemone.PASKIRTA,
                                            VgkPriemone.terminas < siandien).all()
    for priemone in veluojancios:
        priemone.busena = VgkPriemone.VELUOJA
        skelbti("priemone_veluoja", priemone)
    db.session.commit()
    return len(veluojancios)

