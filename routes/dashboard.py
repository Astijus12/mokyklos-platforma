"""Pagrindinis (Dashboard) puslapis su statistika ir diagramomis."""
from datetime import date
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

from models import User, Klase, Mokinys, Diplomas, Skelbimas
from routes.auth import personalas_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def root():
    if current_user.is_authenticated:
        if current_user.yra_tevas:
            return redirect(url_for("parents.dashboard"))
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


def _amziaus_grupe(mokinys, siandien):
    if not mokinys.gimimo_data:
        return "Nežinoma"
    amzius = siandien.year - mokinys.gimimo_data.year - (
        (siandien.month, siandien.day) < (mokinys.gimimo_data.month, mokinys.gimimo_data.day)
    )
    if amzius <= 10:
        return "6–10 m."
    elif amzius <= 13:
        return "11–13 m."
    elif amzius <= 16:
        return "14–16 m."
    else:
        return "17+ m."


@dashboard_bp.route("/dashboard")
@personalas_required
def index():
    visi_mokiniai = Mokinys.query.all()
    siandien = date.today()

    statistika = {
        "vartotoju": User.query.count(),
        "klasiu": Klase.query.count(),
        "mokiniu": len(visi_mokiniai),
        "diplomu": Diplomas.query.count(),
        "skelbimu": Skelbimas.query.count(),
        "autobusas": sum(1 for m in visi_mokiniai if m.mokyklos_autobusas),
        "geroves_komisija": sum(1 for m in visi_mokiniai if m.geroves_komisija),
        "tevu": User.query.filter_by(role="tevas").count(),
    }

    klases = Klase.query.order_by(Klase.pavadinimas).all()
    klasiu_diagrama = {
        "pavadinimai": [k.pavadinimas for k in klases],
        "mokiniu_skaiciai": [k.mokiniu_skaicius for k in klases],
    }

    autobuso_diagrama = {
        "naudoja": statistika["autobusas"],
        "nenaudoja": statistika["mokiniu"] - statistika["autobusas"],
    }

    amziaus_grupes = {}
    for m in visi_mokiniai:
        g = _amziaus_grupe(m, siandien)
        amziaus_grupes[g] = amziaus_grupes.get(g, 0) + 1

    amziaus_tvarka = ["6–10 m.", "11–13 m.", "14–16 m.", "17+ m.", "Nežinoma"]
    amziaus_diagrama = {
        "pavadinimai": [g for g in amziaus_tvarka if g in amziaus_grupes],
        "skaiciai": [amziaus_grupes[g] for g in amziaus_tvarka if g in amziaus_grupes],
    }

    paskutiniai_diplomai = (
        Diplomas.query.order_by(Diplomas.ikeltas.desc()).limit(5).all()
    )
    paskutiniai_skelbimai = (
        Skelbimas.query.order_by(Skelbimas.sukurtas.desc()).limit(3).all()
    )

    return render_template(
        "dashboard.html",
        statistika=statistika,
        klasiu_diagrama=klasiu_diagrama,
        autobuso_diagrama=autobuso_diagrama,
        amziaus_diagrama=amziaus_diagrama,
        paskutiniai_diplomai=paskutiniai_diplomai,
        paskutiniai_skelbimai=paskutiniai_skelbimai,
        klases=klases[:6],
    )
