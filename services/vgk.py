"""Vaiko gerovės komisijos (VGK) logika.

Šiuo metu – suderinamumas su esama mokinio forma: žymė „Gerovės komisija“,
data ir pastabos nuo baigiamojo darbo saugomos ne mokinio stulpeliuose, o
VGK atvejų lentelėje (vgk_atvejai).
"""
from datetime import datetime, time

from models import VgkAtvejis, utc_dabar

NUMATYTOJI_PRIEZASTIS = "Pažymėta mokinio kortelėje."


def atnaujinti_mokinio_zyme(mokinys, pazymeta, data=None, pastabos=None, naudotojas=None):
    """Mokinio formos VGK žymę paverčia VGK atveju.

    - pažymėta, o aktyvaus atvejo nėra – sukuriamas naujas atvejis „Užregistruotas“;
    - pažymėta ir atvejis yra – atnaujinama data ir priežastis, jei jos nurodytos;
    - nepažymėta, o aktyvus atvejis yra – atvejis užbaigiamas.

    Grąžina aktyvų atvejį arba None. Įrašo neišsaugo – tai daro kviečiantis kodas
    (db.session.commit()), kad mokinio ir atvejo pakeitimai būtų vienoje transakcijoje.
    """
    atvejis = mokinys.aktyvus_vgk_atvejis

    if not pazymeta:
        if atvejis is not None:
            atvejis.busena = VgkAtvejis.UZBAIGTAS
            atvejis.uzbaigta = utc_dabar()
        return None

    if atvejis is None:
        atvejis = VgkAtvejis(
            pateike_id=naudotojas.id if naudotojas is not None else None,
            priezastis=pastabos or NUMATYTOJI_PRIEZASTIS,
            busena=VgkAtvejis.UZREGISTRUOTAS,
            sukurta=utc_dabar(),
        )
        mokinys.vgk_atvejai.append(atvejis)
    elif pastabos:
        atvejis.priezastis = pastabos

    # Formoje nurodyta data rodoma kaip „svarstymo data“ – ją saugome kaip atvejo datą
    if data is not None and atvejis.sukurta.date() != data:
        atvejis.sukurta = datetime.combine(data, time())
    return atvejis
