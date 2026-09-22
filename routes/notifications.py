"""Vartotojo pranešimų centras (varpelio ikonoje)."""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user

from models import db, Pranesimas

notifications_bp = Blueprint("notifications", __name__, url_prefix="/pranesimai")


def sukurti(vartotojo_id, pavadinimas, tekstas=None, nuoroda=None, ikona="bell", tipas="info"):
    """Sukuria naują pranešimą vartotojui."""
    p = Pranesimas(
        vartotojo_id=vartotojo_id,
        pavadinimas=pavadinimas,
        tekstas=tekstas,
        nuoroda=nuoroda,
        ikona=ikona,
        tipas=tipas,
    )
    db.session.add(p)
    db.session.commit()
    return p


@notifications_bp.route("/")
@login_required
def sarasas():
    pranesimai = (
        Pranesimas.query
        .filter_by(vartotojo_id=current_user.id)
        .order_by(Pranesimas.sukurtas.desc())
        .limit(50)
        .all()
    )

    for p in pranesimai:
        if not p.perskaitytas:
            p.perskaitytas = True
    db.session.commit()

    return render_template("notifications/sarasas.html", pranesimai=pranesimai)


@notifications_bp.route("/api/skaicius")
@login_required
def api_skaicius():
    """Grąžina neperskaitytų pranešimų skaičių (JSON)."""
    sk = Pranesimas.query.filter_by(
        vartotojo_id=current_user.id,
        perskaitytas=False,
    ).count()
    return jsonify({"skaicius": sk})


@notifications_bp.route("/api/naujausi")
@login_required
def api_naujausi():
    """Grąžina 5 naujausius pranešimus (JSON)."""
    p_list = (
        Pranesimas.query
        .filter_by(vartotojo_id=current_user.id)
        .order_by(Pranesimas.sukurtas.desc())
        .limit(5)
        .all()
    )
    return jsonify({
        "pranesimai": [
            {
                "id": p.id,
                "pavadinimas": p.pavadinimas,
                "tekstas": p.tekstas,
                "nuoroda": p.nuoroda,
                "ikona": p.ikona,
                "tipas": p.tipas,
                "perskaitytas": p.perskaitytas,
                "sukurtas": p.sukurtas.isoformat(),
            }
            for p in p_list
        ]
    })


@notifications_bp.route("/pazymeti-visus", methods=["POST"])
@login_required
def pazymeti_visus():
    Pranesimas.query.filter_by(
        vartotojo_id=current_user.id,
        perskaitytas=False,
    ).update({"perskaitytas": True})
    db.session.commit()
    return redirect(url_for("notifications.sarasas"))
