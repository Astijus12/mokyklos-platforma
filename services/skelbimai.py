"""Skelbimo ir kalendoriaus ryšys: renginio data skelbime -> renginys kalendoriuje.

Jei skelbime nurodoma renginio data, sukuriamas (arba atnaujinamas) susietas renginys.
Jis rodomas mokyklos kalendoriuje (tėvams – jei skelbimas matomas tėvams), o likus
dienai iki jo tėvams siunčiamas priminimas (taisyklė „Priminimas apie renginį“).
Pašalinus datą arba patį skelbimą, renginys pašalinamas, o neišsiųsti pranešimai
apie jį atšaukiami – taip pat, kaip šalinant renginį kalendoriuje.

Funkcijos įrašų neišsaugo (commit) – tai daro kviečiantis kodas kartu su skelbimu.
"""
from models import Renginys, db, utc_dabar
from services.ivykiai import atsaukti_pranesimus, skelbti

# Skelbimo kategorija -> renginio kategorija kalendoriuje (kitos – „Mokyklos renginys“)
_RENGINIO_KATEGORIJOS = {"vgk": "vgk"}


def susieti_su_kalendoriumi(skelbimas, data, laikas=None, vieta=None):
    """Sukuria, atnaujina arba pašalina skelbimo renginį. Grąžina renginį arba None.

    data – renginio data (None – skelbimas be renginio), laikas ir vieta – nebūtini.
    """
    renginys = skelbimas.renginys
    if data is None:
        pasalinti_rengini(skelbimas)
        return None

    naujas = renginys is None
    if naujas:
        renginys = Renginys(vartotojo_id=skelbimas.vartotojo_id, skelbimas=skelbimas)
        db.session.add(renginys)
        pasikeite = False
    else:
        pasikeite = (renginys.pradzios_data, renginys.pradzios_laikas, renginys.vieta) != (data, laikas, vieta)

    renginys.pavadinimas = skelbimas.pavadinimas
    renginys.aprasymas = skelbimas.turinys
    renginys.pradzios_data = data
    renginys.pradzios_laikas = laikas
    renginys.vieta = vieta
    renginys.matomas_tevams = skelbimas.matomas_tevams
    renginys.kategorija = _RENGINIO_KATEGORIJOS.get(skelbimas.kategorija, "mokyklos")

    # Tie patys įvykiai kaip kuriant ar keičiant renginį kalendoriuje
    if naujas:
        skelbti("renginys_sukurtas", renginys)
    elif pasikeite:
        skelbti("renginys_pakeistas", renginys, papildomas_raktas=utc_dabar().strftime("%Y%m%d%H%M%S"))
    return renginys


def pasalinti_rengini(skelbimas):
    """Pašalina skelbimo renginį iš kalendoriaus (jei jis yra)."""
    renginys = skelbimas.renginys
    if renginys is None:
        return False
    atsaukti_pranesimus("renginys", renginys.id)
    skelbti("renginys_atsauktas", renginys)
    skelbimas.renginys = None
    db.session.delete(renginys)
    return True
