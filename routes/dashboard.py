"""Pagrindinis (Dashboard) puslapis su statistika ir diagramomis."""
from collections import Counter
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from models import User, Klase, Mokinys, Diplomas, Skelbimas, Pazymys

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def root():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    statistika = {
        "vartotoju": User.query.count(),
        "klasiu": Klase.query.count(),
        "mokiniu": Mokinys.query.count(),
        "diplomu": Diplomas.query.count(),
        "skelbimu": Skelbimas.query.count(),
        "pazymiu": Pazymys.query.count(),
    }

    klases = Klase.query.order_by(Klase.pavadinimas).all()
    klasiu_diagrama = {
        "pavadinimai": [k.pavadinimas for k in klases],
        "mokiniu_skaiciai": [k.mokiniu_skaicius for k in klases],
    }

    visi_pazymiai = Pazymys.query.all()
    pazymiu_pasiskirstymas = Counter(p.pazymys for p in visi_pazymiai)
    pazymiu_diagrama = {
        "labels": [str(i) for i in range(1, 11)],
        "duomenys": [pazymiu_pasiskirstymas.get(i, 0) for i in range(1, 11)],
    }

    bendras_vidurkis = (
        round(sum(p.pazymys for p in visi_pazymiai) / len(visi_pazymiai), 2)
        if visi_pazymiai else None
    )

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
        pazymiu_diagrama=pazymiu_diagrama,
        bendras_vidurkis=bendras_vidurkis,
        paskutiniai_diplomai=paskutiniai_diplomai,
        paskutiniai_skelbimai=paskutiniai_skelbimai,
        klases=klases[:6],
    )
