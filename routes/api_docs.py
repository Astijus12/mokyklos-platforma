"""Programinės sąsajos dokumentacijos puslapis."""
from flask import Blueprint, render_template
from flask_login import login_required

api_docs_bp = Blueprint("api_docs", __name__, url_prefix="/dokumentacija")


ENDPOINT_APRASYMAI = [
    {
        "grupe": "Sistemos būsena",
        "metodas": "GET",
        "kelias": "/api/v1/health",
        "aprasymas": "Sistemos veikimo patikra - grąžina statusą.",
        "autentikacija": False,
        "atsakymas_pvz": {
            "ok": True,
            "duomenys": {"statusas": "ok", "api_versija": "v1"},
        },
    },
    {
        "grupe": "Autentikacija",
        "metodas": "POST",
        "kelias": "/api/v1/auth/token",
        "aprasymas": "Sukurti prieigos raktą. Reikalinga: email, slaptazodis, opcionaliai dvfa_kodas.",
        "autentikacija": False,
        "uzklausos_pvz": {
            "email": "vartotojas@mokykla.lt",
            "slaptazodis": "slaptas",
            "dvfa_kodas": "123456",
        },
        "atsakymas_pvz": {
            "ok": True,
            "duomenys": {"token": "abc123...", "vartotojas": {"id": 1, "email": "..."}},
        },
    },
    {
        "grupe": "Autentikacija",
        "metodas": "POST",
        "kelias": "/api/v1/auth/logout",
        "aprasymas": "Anuliuoti dabartinį prieigos raktą.",
        "autentikacija": True,
    },
    {
        "grupe": "Vartotojas",
        "metodas": "GET",
        "kelias": "/api/v1/me",
        "aprasymas": "Grąžina prisijungusio vartotojo informaciją.",
        "autentikacija": True,
        "atsakymas_pvz": {
            "ok": True,
            "duomenys": {
                "id": 5, "vardas": "Petras", "pavarde": "Demo",
                "email": "tevas@demo.lt", "role": "tevas"
            },
        },
    },
    {
        "grupe": "Tėvų sąsaja",
        "metodas": "GET",
        "kelias": "/api/v1/children",
        "aprasymas": "Tėvo priskirtų vaikų sąrašas. Prieinamas tik tėvams.",
        "autentikacija": True,
    },
    {
        "grupe": "Tėvų sąsaja",
        "metodas": "GET",
        "kelias": "/api/v1/children/<id>",
        "aprasymas": "Konkretaus vaiko duomenys. Tėvas mato tik savo vaikus.",
        "autentikacija": True,
    },
    {
        "grupe": "Skelbimai",
        "metodas": "GET",
        "kelias": "/api/v1/announcements",
        "aprasymas": "Skelbimų sąrašas. Tėvams grąžinami tik viešieji.",
        "autentikacija": True,
    },
    {
        "grupe": "Kontaktai",
        "metodas": "GET",
        "kelias": "/api/v1/contacts",
        "aprasymas": "Klasių vadovų kontaktai. Tėvams - tik jų vaikų klasių vadovų.",
        "autentikacija": True,
    },
]


@api_docs_bp.route("/api")
@login_required
def api():
    grupes = {}
    for e in ENDPOINT_APRASYMAI:
        grupes.setdefault(e["grupe"], []).append(e)

    return render_template("api_docs/api.html", grupes=grupes)
