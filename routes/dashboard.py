"""Pagrindinis (Dashboard) puslapis su statistika ir diagramomis."""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from models import User, Klase, Mokinys, Diplomas, Skelbimas

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def root():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    visi_mokiniai = Mokinys.query.all()

    statistika = {
        "vartotoju": User.query.count(),
        "klasiu": Klase.query.count(),
        "mokiniu": len(visi_mokiniai),
        "diplomu": Diplomas.query.count(),
        "skelbimu": Skelbimas.query.count(),
        "autobusas": sum(1 for m in visi_mokiniai if m.mokyklos_autobusas),
        "geroves_komisija": sum(1 for m in visi_mokiniai if m.geroves_komisija),
    }

    klases = Klase.query.order_by(Klase.pavadinimas).all()
    klasiu_diagrama = {
        "pavadinimai": [k.pavadinimas for k in klases],
        "mokiniu_skaiciai": [k.mokiniu_skaicius for k in klases],
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
        paskutiniai_diplomai=paskutiniai_diplomai,
        paskutiniai_skelbimai=paskutiniai_skelbimai,
        klases=klases[:6],
    )
