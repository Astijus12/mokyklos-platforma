"""Vartotojų (mokytojų) valdymas - prieinamas tik administratoriams."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from models import db, User, Mokinys, Klase
from routes.auth import admin_required

users_bp = Blueprint("users", __name__, url_prefix="/vartotojai")


@users_bp.route("/")
@admin_required
def saraso():
    vartotojai = User.query.order_by(User.pavarde, User.vardas).all()
    return render_template("users/list.html", vartotojai=vartotojai)


@users_bp.route("/naujas", methods=["GET", "POST"])
@admin_required
def naujas():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        slaptazodis = request.form.get("slaptazodis", "")

        if User.query.filter_by(email=email).first():
            flash("Vartotojas su tokiu el. paštu jau egzistuoja.", "danger")
        elif len(slaptazodis) < 6:
            flash("Slaptažodis turi būti bent 6 simbolių.", "danger")
        else:
            vartotojas = User(
                vardas=request.form.get("vardas", "").strip(),
                pavarde=request.form.get("pavarde", "").strip(),
                email=email,
                telefonas=request.form.get("telefonas", "").strip() or None,
                role=request.form.get("role", "mokytojas"),
            )
            vartotojas.nustatyti_slaptazodi(slaptazodis)
            db.session.add(vartotojas)
            db.session.commit()
            flash(f"Vartotojas {vartotojas.pilnas_vardas} sukurtas.", "success")
            return redirect(url_for("users.saraso"))

    return render_template("users/form.html", vartotojas=None)


@users_bp.route("/<int:vartotojo_id>/redaguoti", methods=["GET", "POST"])
@admin_required
def redaguoti(vartotojo_id):
    vartotojas = User.query.get_or_404(vartotojo_id)

    if request.method == "POST":
        vartotojas.vardas = request.form.get("vardas", "").strip()
        vartotojas.pavarde = request.form.get("pavarde", "").strip()
        vartotojas.email = request.form.get("email", "").strip().lower()
        vartotojas.telefonas = request.form.get("telefonas", "").strip() or None
        vartotojas.role = request.form.get("role", "mokytojas")

        naujas_slaptazodis = request.form.get("slaptazodis", "")
        if naujas_slaptazodis:
            if len(naujas_slaptazodis) < 6:
                flash("Slaptažodis turi būti bent 6 simbolių.", "danger")
                return render_template("users/form.html", vartotojas=vartotojas)
            vartotojas.nustatyti_slaptazodi(naujas_slaptazodis)

        db.session.commit()
        flash("Vartotojo duomenys atnaujinti.", "success")
        return redirect(url_for("users.saraso"))

    return render_template("users/form.html", vartotojas=vartotojas)


@users_bp.route("/<int:vartotojo_id>/salinti", methods=["POST"])
@admin_required
def salinti(vartotojo_id):
    if vartotojo_id == current_user.id:
        flash("Negalite pašalinti savęs.", "danger")
        return redirect(url_for("users.saraso"))

    vartotojas = User.query.get_or_404(vartotojo_id)
    vardas = vartotojas.pilnas_vardas
    db.session.delete(vartotojas)
    db.session.commit()
    flash(f"Vartotojas {vardas} pašalintas.", "info")
    return redirect(url_for("users.saraso"))


@users_bp.route("/<int:vartotojo_id>/vaikai", methods=["GET", "POST"])
@admin_required
def vaikai(vartotojo_id):
    """Priskirti tėvui jo vaikus (mokinius)."""
    tevas = User.query.get_or_404(vartotojo_id)

    if tevas.role != "tevas":
        flash("Vaikų priskyrimas galimas tik tėvo rolės paskyroms.", "warning")
        return redirect(url_for("users.redaguoti", vartotojo_id=tevas.id))

    if request.method == "POST":
        priskirtu_ids = set(request.form.getlist("vaiku_ids", type=int))

        naujas_sarasas = Mokinys.query.filter(Mokinys.id.in_(priskirtu_ids)).all() if priskirtu_ids else []

        tevas.vaikai = naujas_sarasas
        db.session.commit()
        flash(
            f"Tėvui {tevas.pilnas_vardas} priskirti {len(naujas_sarasas)} vaikai.",
            "success",
        )
        return redirect(url_for("users.saraso"))

    klases = Klase.query.order_by(Klase.pavadinimas).all()
    priskirtu_ids = {v.id for v in tevas.vaikai}

    return render_template(
        "users/vaikai.html",
        tevas=tevas,
        klases=klases,
        priskirtu_ids=priskirtu_ids,
    )
