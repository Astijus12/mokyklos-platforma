"""Pažymių valdymas."""
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from models import db, Pazymys, Mokinys, DALYKAI

grades_bp = Blueprint("grades", __name__, url_prefix="/pazymiai")


def _parse_data(reiksme):
    if not reiksme:
        return date.today()
    try:
        return datetime.strptime(reiksme, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


@grades_bp.route("/")
@login_required
def saraso():
    """Visi pažymiai - filtruojami pagal dalyką arba klasę."""
    dalykas = request.args.get("dalykas", "").strip()

    query = Pazymys.query.join(Mokinys)
    if dalykas:
        query = query.filter(Pazymys.dalykas == dalykas)

    pazymiai = query.order_by(Pazymys.data.desc()).limit(100).all()

    return render_template(
        "grades/list.html",
        pazymiai=pazymiai,
        dalykai=DALYKAI,
        pasirinktas_dalykas=dalykas,
    )


@grades_bp.route("/naujas/<int:mokinio_id>", methods=["GET", "POST"])
@login_required
def naujas(mokinio_id):
    mokinys = Mokinys.query.get_or_404(mokinio_id)

    if request.method == "POST":
        try:
            pazymys_reiksme = int(request.form.get("pazymys", 0))
        except ValueError:
            pazymys_reiksme = 0

        dalykas = request.form.get("dalykas", "").strip()

        if pazymys_reiksme < 1 or pazymys_reiksme > 10:
            flash("Pažymys turi būti nuo 1 iki 10.", "danger")
        elif dalykas not in DALYKAI:
            flash("Pasirinkite dalyką iš sąrašo.", "danger")
        else:
            pazymys = Pazymys(
                mokinio_id=mokinys.id,
                mokytojo_id=current_user.id,
                dalykas=dalykas,
                pazymys=pazymys_reiksme,
                komentaras=request.form.get("komentaras", "").strip() or None,
                data=_parse_data(request.form.get("data")),
            )
            db.session.add(pazymys)
            db.session.commit()
            flash(f"Pažymys mokiniui {mokinys.pilnas_vardas} įrašytas.", "success")
            return redirect(url_for("students.detales", mokinio_id=mokinys.id))

    return render_template(
        "grades/form.html",
        mokinys=mokinys,
        dalykai=DALYKAI,
        siandien=date.today().isoformat(),
    )


@grades_bp.route("/<int:pazymio_id>/salinti", methods=["POST"])
@login_required
def salinti(pazymio_id):
    pazymys = Pazymys.query.get_or_404(pazymio_id)

    if not current_user.yra_administratorius and pazymys.mokytojo_id != current_user.id:
        abort(403)

    mokinio_id = pazymys.mokinio_id
    db.session.delete(pazymys)
    db.session.commit()
    flash("Pažymys pašalintas.", "info")
    return redirect(url_for("students.detales", mokinio_id=mokinio_id))
