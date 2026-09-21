"""Prisijungimo ir atsijungimo logika."""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
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


def tevas_required(f):
    """Dekoratorius - leidžia pasiekti tik tėvams."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.yra_tevas:
            flash("Šis puslapis prieinamas tik tėvams.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated_function


def personalas_required(f):
    """Dekoratorius - leidžia pasiekti tik mokytojams ir administratoriams (ne tėvams)."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.yra_tevas:
            flash("Šis puslapis prieinamas tik mokyklos darbuotojams.", "danger")
            return redirect(url_for("parents.dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def _po_prisijungimo_url(vartotojas):
    """Grąžina URL, į kurį nukreipti pagal vartotojo rolę."""
    if vartotojas.yra_tevas:
        return url_for("parents.dashboard")
    return url_for("dashboard.index")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_po_prisijungimo_url(current_user))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        slaptazodis = request.form.get("slaptazodis", "")

        vartotojas = User.query.filter_by(email=email).first()

        if vartotojas and vartotojas.patikrinti_slaptazodi(slaptazodis):
            if vartotojas.dvfa_ijungtas:
                session["dvfa_lauke_vartotojo_id"] = vartotojas.id
                return redirect(url_for("security.patvirtinti"))

            login_user(vartotojas, remember=True)
            flash(f"Sveiki sugrįžę, {vartotojas.vardas}!", "success")
            kitas = request.args.get("next")
            return redirect(kitas or _po_prisijungimo_url(vartotojas))

        flash("Neteisingas el. paštas arba slaptažodis.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sėkmingai atsijungėte.", "info")
    return redirect(url_for("auth.login"))
