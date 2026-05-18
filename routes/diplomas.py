"""Diplomų ir pažymų valdymas - įkėlimas, peržiūra, atsisiuntimas."""
import os
import uuid
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, current_app, send_from_directory, abort,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import db, Diplomas, User

diplomas_bp = Blueprint("diplomas", __name__, url_prefix="/diplomai")


def _leistinas_failas(failo_vardas):
    return (
        "." in failo_vardas
        and failo_vardas.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


def _parse_data(reiksme):
    if not reiksme:
        return None
    try:
        return datetime.strptime(reiksme, "%Y-%m-%d").date()
    except ValueError:
        return None


@diplomas_bp.route("/")
@login_required
def saraso():
    rodyti_visus = request.args.get("visi") == "1"

    if rodyti_visus or current_user.yra_administratorius:
        diplomai = Diplomas.query.order_by(Diplomas.ikeltas.desc()).all()
    else:
        diplomai = (
            Diplomas.query.filter_by(vartotojo_id=current_user.id)
            .order_by(Diplomas.ikeltas.desc())
            .all()
        )

    return render_template("diplomas/list.html", diplomai=diplomai, rodyti_visus=rodyti_visus)


@diplomas_bp.route("/ikelti", methods=["GET", "POST"])
@login_required
def ikelti():
    if request.method == "POST":
        failas = request.files.get("failas")

        if not failas or failas.filename == "":
            flash("Pasirinkite failą įkėlimui.", "danger")
            return redirect(request.url)

        if not _leistinas_failas(failas.filename):
            flash("Leidžiami tik PDF, PNG, JPG, JPEG failai.", "danger")
            return redirect(request.url)

        originalus_vardas = secure_filename(failas.filename)
        plesinys = originalus_vardas.rsplit(".", 1)[1].lower()
        unikalus_vardas = f"{uuid.uuid4().hex}.{plesinys}"
        kelias = os.path.join(current_app.config["UPLOAD_FOLDER"], unikalus_vardas)
        failas.save(kelias)

        diplomas = Diplomas(
            pavadinimas=request.form.get("pavadinimas", "").strip() or originalus_vardas,
            aprasymas=request.form.get("aprasymas", "").strip() or None,
            seminaras=request.form.get("seminaras", "").strip() or None,
            isdavimo_data=_parse_data(request.form.get("isdavimo_data")),
            failo_kelias=unikalus_vardas,
            originalus_failo_vardas=originalus_vardas,
            failo_tipas=plesinys,
            vartotojo_id=current_user.id,
        )
        db.session.add(diplomas)
        db.session.commit()
        flash("Diplomas sėkmingai įkeltas!", "success")
        return redirect(url_for("diplomas.saraso"))

    return render_template("diplomas/upload.html")


@diplomas_bp.route("/<int:diplomo_id>/atsisiusti")
@login_required
def atsisiusti(diplomo_id):
    diplomas = Diplomas.query.get_or_404(diplomo_id)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        diplomas.failo_kelias,
        as_attachment=True,
        download_name=diplomas.originalus_failo_vardas,
    )


@diplomas_bp.route("/<int:diplomo_id>/perziureti")
@login_required
def perziureti(diplomo_id):
    diplomas = Diplomas.query.get_or_404(diplomo_id)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        diplomas.failo_kelias,
        as_attachment=False,
    )


@diplomas_bp.route("/<int:diplomo_id>/salinti", methods=["POST"])
@login_required
def salinti(diplomo_id):
    diplomas = Diplomas.query.get_or_404(diplomo_id)

    if not current_user.yra_administratorius and diplomas.vartotojo_id != current_user.id:
        abort(403)

    kelias = os.path.join(current_app.config["UPLOAD_FOLDER"], diplomas.failo_kelias)
    if os.path.exists(kelias):
        os.remove(kelias)

    db.session.delete(diplomas)
    db.session.commit()
    flash("Diplomas pašalintas.", "info")
    return redirect(url_for("diplomas.saraso"))
