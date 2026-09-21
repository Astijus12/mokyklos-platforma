"""Tėvų portalo maršrutai - tėvai mato tik savo vaikų duomenis."""
from flask import Blueprint, render_template, abort, redirect, url_for
from flask_login import current_user

from models import Skelbimas
from routes.auth import tevas_required

parents_bp = Blueprint("parents", __name__, url_prefix="/tevams")


def _gauti_vaika_ar_404(vaiko_id):
    """Patikrina, ar dabartinis tėvas turi teisę matyti šį vaiką."""
    vaikas = current_user.vaikai.filter_by(id=vaiko_id).first()
    if vaikas is None:
        abort(404)
    return vaikas


@parents_bp.route("/")
@tevas_required
def dashboard():
    """Tėvų pagrindinis puslapis - vaikų sąrašas ir naujausi skelbimai."""
    vaikai = current_user.vaikai.all()

    paskutiniai_skelbimai = (
        Skelbimas.query
        .filter_by(matomas_tevams=True)
        .order_by(Skelbimas.sukurtas.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "parents/dashboard.html",
        vaikai=vaikai,
        paskutiniai_skelbimai=paskutiniai_skelbimai,
    )


@parents_bp.route("/vaikas/<int:vaiko_id>")
@tevas_required
def vaikas(vaiko_id):
    """Detalus vaiko profilio puslapis."""
    vaikas = _gauti_vaika_ar_404(vaiko_id)
    return render_template("parents/vaikas.html", vaikas=vaikas)


@parents_bp.route("/skelbimai")
@tevas_required
def skelbimai():
    """Skelbimai, pažymėti kaip matomi tėvams."""
    visi_skelbimai = (
        Skelbimas.query
        .filter_by(matomas_tevams=True)
        .order_by(Skelbimas.svarbus.desc(), Skelbimas.sukurtas.desc())
        .all()
    )
    return render_template("parents/skelbimai.html", skelbimai=visi_skelbimai)


@parents_bp.route("/kontaktai")
@tevas_required
def kontaktai():
    """Klasių vadovų kontaktai (tik tų klasių, kuriose mokosi mano vaikai)."""
    vaikai = current_user.vaikai.all()
    kontaktai_sarasas = []
    matyti_vadovai = set()

    for vaikas in vaikai:
        klase = vaikas.klase
        if klase and klase.vadovas and klase.vadovas.id not in matyti_vadovai:
            matyti_vadovai.add(klase.vadovas.id)
            kontaktai_sarasas.append({
                "vadovas": klase.vadovas,
                "klase": klase,
                "vaikai": [v for v in vaikai if v.klases_id == klase.id],
            })

    return render_template("parents/kontaktai.html", kontaktai=kontaktai_sarasas)
