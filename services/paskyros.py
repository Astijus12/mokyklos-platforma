"""Naujų tėvų paskyrų kvietimai: vienkartinė nuoroda slaptažodžiui susikurti (FR-I06).

Slaptažodis el. laišku nesiunčiamas. Vietoj jo kvietime pateikiama pasirašyta
nuoroda, galiojanti 14 dienų. Į žetoną įrašoma dabartinės slaptažodžio maišos
pabaiga, todėl nustačius slaptažodį ta pati nuoroda nebegalioja (vienkartinė).
"""
import secrets

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import User, db

GALIOJIMAS_S = 14 * 24 * 3600
_DRUSKA = "slaptazodzio-nustatymas"


def _serializatorius():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_DRUSKA)


def atsitiktinis_slaptazodis():
    """Laikinas slaptažodis naujai paskyrai – niekam nežinomas ir nesiunčiamas."""
    return secrets.token_urlsafe(24)


def slaptazodzio_zetonas(naudotojas):
    return _serializatorius().dumps({"id": naudotojas.id, "h": naudotojas.slaptazodzio_hash[-12:]})


def naudotojas_pagal_zetona(zetonas):
    """Grąžina naudotoją arba None, jei nuoroda netinkama, pasibaigusi ar jau panaudota."""
    try:
        duomenys = _serializatorius().loads(zetonas, max_age=GALIOJIMAS_S)
    except (SignatureExpired, BadSignature):
        return None
    naudotojas = db.session.get(User, duomenys.get("id"))
    if naudotojas is None or naudotojas.slaptazodzio_hash[-12:] != duomenys.get("h"):
        return None
    return naudotojas


def nustatyti_slaptazodi(naudotojas, slaptazodis, pakartotas):
    """Grąžina klaidos tekstą arba None, jei slaptažodis nustatytas."""
    if len(slaptazodis or "") < 8:
        return "Slaptažodis turi būti bent 8 simbolių."
    if slaptazodis != pakartotas:
        return "Slaptažodžiai nesutampa."
    naudotojas.nustatyti_slaptazodi(slaptazodis)
    db.session.commit()
    return None
