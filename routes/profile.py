"""Mano profilio valdymas - peržiūra ir slaptažodžio keitimas."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db, Diplomas, Skelbimas

profile_bp = Blueprint("profile", __name__, url_prefix="/profilis")


@profile_bp.route("/")
@login_required
def index():
    diplomu_skaicius = Diplomas.query.filter_by(vartotojo_id=current_user.id).count()
    skelbimu_skaicius = Skelbimas.query.filter_by(vartotojo_id=current_user.id).count()
    mano_diplomai = (
        Diplomas.query.filter_by(vartotojo_id=current_user.id)
        .order_by(Diplomas.ikeltas.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "profile/index.html",
        diplomu_skaicius=diplomu_skaicius,
        skelbimu_skaicius=skelbimu_skaicius,
        mano_diplomai=mano_diplomai,
    )


@profile_bp.route("/redaguoti", methods=["GET", "POST"])
@login_required
def redaguoti():
    if request.method == "POST":
        current_user.vardas = request.form.get("vardas", "").strip()
        current_user.pavarde = request.form.get("pavarde", "").strip()
        current_user.email = request.form.get("email", "").strip().lower()
        db.session.commit()
        flash("Profilio duomenys atnaujinti.", "success")
        return redirect(url_for("profile.index"))

    return render_template("profile/edit.html")


@profile_bp.route("/slaptazodis", methods=["GET", "POST"])
@login_required
def keisti_slaptazodi():
    if request.method == "POST":
        senas = request.form.get("senas_slaptazodis", "")
        naujas = request.form.get("naujas_slaptazodis", "")
        patvirtinimas = request.form.get("patvirtinimas", "")

        if not current_user.patikrinti_slaptazodi(senas):
            flash("Senas slaptažodis neteisingas.", "danger")
        elif len(naujas) < 6:
            flash("Naujas slaptažodis turi būti bent 6 simbolių.", "danger")
        elif naujas != patvirtinimas:
            flash("Nauji slaptažodžiai nesutampa.", "danger")
        else:
            current_user.nustatyti_slaptazodi(naujas)
            db.session.commit()
            flash("Slaptažodis sėkmingai pakeistas!", "success")
            return redirect(url_for("profile.index"))

    return render_template("profile/password.html")
