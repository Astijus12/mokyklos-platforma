"""REST API v1 - skirta mobiliajai aplikacijai ir kitiems klientams.

Autentikacija: Bearer token per `Authorization: Bearer <token>` antraštę.
Atsakymai visada JSON formatu.
"""
from functools import wraps

import pyotp
from flask import Blueprint, request, jsonify, g

from models import db, User, Mokinys, Skelbimas

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _atsakymas(duomenys=None, klaida=None, statusas=200):
    """Vieninga JSON atsakymo forma."""
    if klaida:
        return jsonify({"ok": False, "klaida": klaida}), statusas
    return jsonify({"ok": True, "duomenys": duomenys}), statusas


def token_required(f):
    """Dekoratorius - reikalauja galiojančio API tokeno."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        antraste = request.headers.get("Authorization", "")
        if not antraste.startswith("Bearer "):
            return _atsakymas(klaida="Trūksta 'Authorization: Bearer <token>' antraštės", statusas=401)

        tokenas = antraste[len("Bearer "):].strip()
        vartotojas = User.rasti_pagal_api_tokena(tokenas)

        if vartotojas is None:
            return _atsakymas(klaida="Neteisingas arba pasibaigęs API tokenas", statusas=401)

        g.api_vartotojas = vartotojas
        return f(*args, **kwargs)
    return wrapper


def _serializuoti_vartotoja(v):
    return {
        "id": v.id,
        "vardas": v.vardas,
        "pavarde": v.pavarde,
        "pilnas_vardas": v.pilnas_vardas,
        "email": v.email,
        "telefonas": v.telefonas,
        "role": v.role,
        "dvfa_ijungtas": v.dvfa_ijungtas,
    }


def _serializuoti_vaika(m, tik_pagrindiniai=False):
    duomenys = {
        "id": m.id,
        "vardas": m.vardas,
        "pavarde": m.pavarde,
        "pilnas_vardas": m.pilnas_vardas,
        "klase": {
            "id": m.klase.id,
            "pavadinimas": m.klase.pavadinimas,
        } if m.klase else None,
    }
    if tik_pagrindiniai:
        return duomenys

    duomenys.update({
        "gimimo_data": m.gimimo_data.isoformat() if m.gimimo_data else None,
        "email": m.email,
        "telefonas": m.telefonas,
        "adresas": m.adresas,
        "mokyklos_autobusas": m.mokyklos_autobusas,
        "geroves_komisija": {
            "aktyvus": m.geroves_komisija,
            "data": m.geroves_komisija_data.isoformat() if m.geroves_komisija_data else None,
            "pastabos": m.geroves_komisija_pastabos,
        },
        "klases_vadovas": (
            {
                "vardas": m.klase.vadovas.pilnas_vardas,
                "email": m.klase.vadovas.email,
                "telefonas": m.klase.vadovas.telefonas,
            }
            if m.klase and m.klase.vadovas
            else None
        ),
    })
    return duomenys


def _serializuoti_skelbima(s):
    return {
        "id": s.id,
        "pavadinimas": s.pavadinimas,
        "turinys": s.turinys,
        "svarbus": s.svarbus,
        "matomas_tevams": s.matomas_tevams,
        "autorius": s.autorius.pilnas_vardas if s.autorius else None,
        "sukurtas": s.sukurtas.isoformat(),
    }


@api_bp.route("/health")
def health():
    """Serverio būsenos patikra - nereikia autentikacijos."""
    return _atsakymas({"statusas": "ok", "api_versija": "v1"})


@api_bp.route("/auth/token", methods=["POST"])
def prisijungti():
    """Sukurti API tokeną iš el. pašto + slaptažodžio (+ opcionaliai 2FA kodo)."""
    duomenys = request.get_json(silent=True) or {}
    email = (duomenys.get("email") or "").strip().lower()
    slaptazodis = duomenys.get("slaptazodis") or ""
    dvfa_kodas = (duomenys.get("dvfa_kodas") or "").strip().replace(" ", "")

    if not email or not slaptazodis:
        return _atsakymas(klaida="Reikalingi laukai: email, slaptazodis", statusas=400)

    vartotojas = User.query.filter_by(email=email).first()
    if not vartotojas or not vartotojas.patikrinti_slaptazodi(slaptazodis):
        return _atsakymas(klaida="Neteisingas el. paštas arba slaptažodis", statusas=401)

    if vartotojas.dvfa_ijungtas:
        if not dvfa_kodas:
            return _atsakymas(
                klaida="Būtinas 2FA kodas",
                statusas=401,
            )
        totp = pyotp.TOTP(vartotojas.dvfa_paslaptis)
        if not totp.verify(dvfa_kodas, valid_window=1):
            return _atsakymas(klaida="Neteisingas 2FA kodas", statusas=401)

    tokenas = vartotojas.sugeneruoti_api_tokena()
    db.session.commit()

    return _atsakymas({
        "token": tokenas,
        "vartotojas": _serializuoti_vartotoja(vartotojas),
    })


@api_bp.route("/auth/logout", methods=["POST"])
@token_required
def atsijungti():
    """Anuliuoti dabartinį API tokeną."""
    g.api_vartotojas.anuliuoti_api_tokena()
    db.session.commit()
    return _atsakymas({"pranesimas": "Tokenas anuliuotas"})


@api_bp.route("/me")
@token_required
def apie_mane():
    """Dabartinio vartotojo informacija."""
    return _atsakymas(_serializuoti_vartotoja(g.api_vartotojas))


@api_bp.route("/children")
@token_required
def vaikai():
    """Vaikų sąrašas (tik tėvams)."""
    v = g.api_vartotojas
    if not v.yra_tevas:
        return _atsakymas(klaida="Šis maršrutas skirtas tik tėvų paskyroms", statusas=403)

    duomenys = [_serializuoti_vaika(m, tik_pagrindiniai=True) for m in v.vaikai]
    return _atsakymas(duomenys)


@api_bp.route("/children/<int:vaiko_id>")
@token_required
def vaikas(vaiko_id):
    """Detali vieno vaiko informacija (tėvas mato tik savo vaikus)."""
    v = g.api_vartotojas
    if not v.yra_tevas:
        return _atsakymas(klaida="Šis maršrutas skirtas tik tėvų paskyroms", statusas=403)

    vaikas = v.vaikai.filter_by(id=vaiko_id).first()
    if vaikas is None:
        return _atsakymas(klaida="Vaikas nerastas arba nepriskirtas jums", statusas=404)

    return _atsakymas(_serializuoti_vaika(vaikas))


@api_bp.route("/announcements")
@token_required
def skelbimai():
    """Skelbimai. Tėvams grąžinami tik viešieji."""
    v = g.api_vartotojas
    query = Skelbimas.query
    if v.yra_tevas:
        query = query.filter_by(matomas_tevams=True)

    sarasas = query.order_by(
        Skelbimas.svarbus.desc(), Skelbimas.sukurtas.desc()
    ).all()

    return _atsakymas([_serializuoti_skelbima(s) for s in sarasas])


@api_bp.route("/contacts")
@token_required
def kontaktai():
    """Klasių vadovų kontaktai. Tėvams - tik jų vaikų klasių vadovai."""
    v = g.api_vartotojas

    if v.yra_tevas:
        matyti = {}
        for vaikas in v.vaikai:
            if vaikas.klase and vaikas.klase.vadovas:
                vadovas = vaikas.klase.vadovas
                if vadovas.id not in matyti:
                    matyti[vadovas.id] = {
                        "vadovas": _serializuoti_vartotoja(vadovas),
                        "klase": vaikas.klase.pavadinimas,
                    }
        return _atsakymas(list(matyti.values()))

    from models import Klase
    klases = Klase.query.filter(Klase.vadovo_id.isnot(None)).all()
    return _atsakymas([
        {
            "vadovas": _serializuoti_vartotoja(k.vadovas),
            "klase": k.pavadinimas,
        }
        for k in klases
    ])
