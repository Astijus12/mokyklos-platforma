"""Skelbimų / pranešimų valdymas."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required
from routes.auth import personalas_required, current_user

from models import db, Skelbimas

announcements_bp = Blueprint("announcements", __name__, url_prefix="/skelbimai")


@announcements_bp.route("/")
@personalas_required
def saraso():
    skelbimai = Skelbimas.query.order_by(
        Skelbimas.svarbus.desc(), Skelbimas.sukurtas.desc()
    ).all()
    return render_template("announcements/list.html", skelbimai=skelbimai)


@announcements_bp.route("/naujas", methods=["GET", "POST"])
@personalas_required
def naujas():
    if request.method == "POST":
        pavadinimas = request.form.get("pavadinimas", "").strip()
        turinys = request.form.get("turinys", "").strip()
        svarbus = request.form.get("svarbus") == "on"

        if not pavadinimas or not turinys:
            flash("Pavadinimas ir turinys yra privalomi.", "danger")
        else:
            skelbimas = Skelbimas(
                pavadinimas=pavadinimas,
                turinys=turinys,
                svarbus=svarbus,
                matomas_tevams=request.form.get("matomas_tevams") == "on",
                vartotojo_id=current_user.id,
            )
            db.session.add(skelbimas)
            db.session.commit()
            flash("Skelbimas paskelbtas!", "success")
            return redirect(url_for("announcements.saraso"))

    return render_template("announcements/form.html", skelbimas=None)


@announcements_bp.route("/<int:skelbimo_id>")
@personalas_required
def perziureti(skelbimo_id):
    skelbimas = Skelbimas.query.get_or_404(skelbimo_id)
    return render_template("announcements/detail.html", skelbimas=skelbimas)


@announcements_bp.route("/<int:skelbimo_id>/redaguoti", methods=["GET", "POST"])
@personalas_required
def redaguoti(skelbimo_id):
    skelbimas = Skelbimas.query.get_or_404(skelbimo_id)

    if not current_user.yra_administratorius and skelbimas.vartotojo_id != current_user.id:
        abort(403)

    if request.method == "POST":
        skelbimas.pavadinimas = request.form.get("pavadinimas", "").strip()
        skelbimas.turinys = request.form.get("turinys", "").strip()
        skelbimas.svarbus = request.form.get("svarbus") == "on"
        skelbimas.matomas_tevams = request.form.get("matomas_tevams") == "on"
        db.session.commit()
        flash("Skelbimas atnaujintas.", "success")
        return redirect(url_for("announcements.perziureti", skelbimo_id=skelbimas.id))

    return render_template("announcements/form.html", skelbimas=skelbimas)


@announcements_bp.route("/<int:skelbimo_id>/salinti", methods=["POST"])
@personalas_required
def salinti(skelbimo_id):
    skelbimas = Skelbimas.query.get_or_404(skelbimo_id)

    if not current_user.yra_administratorius and skelbimas.vartotojo_id != current_user.id:
        abort(403)

    db.session.delete(skelbimas)
    db.session.commit()
    flash("Skelbimas pašalintas.", "info")
    return redirect(url_for("announcements.saraso"))
