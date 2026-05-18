"""Prisijungimo ir atsijungimo logika."""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from models import db, User

auth_bp = Blueprint("auth", __name__)


def admin_required(f):
    """Dekoratorius - leidžia pasiekti tik administratoriams."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.yra_administratorius:
            flash("Šis puslapis prieinamas tik administratoriams.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        slaptazodis = request.form.get("slaptazodis", "")

        vartotojas = User.query.filter_by(email=email).first()

        if vartotojas and vartotojas.patikrinti_slaptazodi(slaptazodis):
            login_user(vartotojas, remember=True)
            flash(f"Sveiki sugrįžę, {vartotojas.vardas}!", "success")
            kitas = request.args.get("next")
            return redirect(kitas or url_for("dashboard.index"))

        flash("Neteisingas el. paštas arba slaptažodis.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sėkmingai atsijungėte.", "info")
    return redirect(url_for("auth.login"))
