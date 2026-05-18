"""Klasių valdymo puslapiai."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db, Klase, User, Mokinys
from routes.auth import admin_required

classes_bp = Blueprint("classes", __name__, url_prefix="/klases")


@classes_bp.route("/")
@login_required
def saraso():
    klases = Klase.query.order_by(Klase.pavadinimas).all()
    return render_template("classes/list.html", klases=klases)


@classes_bp.route("/<int:klases_id>")
@login_required
def detales(klases_id):
    klase = Klase.query.get_or_404(klases_id)
    mokiniai = (
        Mokinys.query.filter_by(klases_id=klases_id)
        .order_by(Mokinys.pavarde, Mokinys.vardas)
        .all()
    )
    return render_template("classes/detail.html", klase=klase, mokiniai=mokiniai)


@classes_bp.route("/nauja", methods=["GET", "POST"])
@admin_required
def nauja():
    if request.method == "POST":
        pavadinimas = request.form.get("pavadinimas", "").strip().upper()
        mokslo_metai = request.form.get("mokslo_metai", "2025-2026").strip()
        vadovo_id = request.form.get("vadovo_id") or None

        if not pavadinimas:
            flash("Įveskite klasės pavadinimą.", "danger")
        elif Klase.query.filter_by(pavadinimas=pavadinimas).first():
            flash(f"Klasė '{pavadinimas}' jau egzistuoja.", "danger")
        else:
            klase = Klase(
                pavadinimas=pavadinimas,
                mokslo_metai=mokslo_metai,
                vadovo_id=int(vadovo_id) if vadovo_id else None,
            )
            db.session.add(klase)
            db.session.commit()
            flash(f"Klasė '{pavadinimas}' sėkmingai sukurta!", "success")
            return redirect(url_for("classes.saraso"))

    mokytojai = User.query.order_by(User.pavarde).all()
    return render_template("classes/form.html", mokytojai=mokytojai, klase=None)


@classes_bp.route("/<int:klases_id>/redaguoti", methods=["GET", "POST"])
@admin_required
def redaguoti(klases_id):
    klase = Klase.query.get_or_404(klases_id)

    if request.method == "POST":
        klase.pavadinimas = request.form.get("pavadinimas", "").strip().upper()
        klase.mokslo_metai = request.form.get("mokslo_metai", "").strip()
        vadovo_id = request.form.get("vadovo_id") or None
        klase.vadovo_id = int(vadovo_id) if vadovo_id else None
        db.session.commit()
        flash(f"Klasė '{klase.pavadinimas}' atnaujinta.", "success")
        return redirect(url_for("classes.detales", klases_id=klase.id))

    mokytojai = User.query.order_by(User.pavarde).all()
    return render_template("classes/form.html", mokytojai=mokytojai, klase=klase)


@classes_bp.route("/<int:klases_id>/salinti", methods=["POST"])
@admin_required
def salinti(klases_id):
    klase = Klase.query.get_or_404(klases_id)
    pavadinimas = klase.pavadinimas
    db.session.delete(klase)
    db.session.commit()
    flash(f"Klasė '{pavadinimas}' pašalinta.", "info")
    return redirect(url_for("classes.saraso"))
