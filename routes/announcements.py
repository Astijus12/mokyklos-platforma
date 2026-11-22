"""Skelbimų / pranešimų valdymas.

BD: skelbime galima nurodyti renginio datą – tada skelbimas rodomas ir mokyklos
kalendoriuje (services/skelbimai.py).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required
from routes.auth import personalas_required, current_user

from models import db, Skelbimas
from services.ivykiai import skelbti
from services.kalendorius import data_is_formos, laikas_is_formos
from services.skelbimai import pasalinti_rengini, susieti_su_kalendoriumi

announcements_bp = Blueprint("announcements", __name__, url_prefix="/skelbimai")


def _renginio_laukai(forma):
    """Renginio data, laikas ir vieta iš formos. Grąžina (data, laikas, vieta, klaida)."""
    data_tekstas = forma.get("renginio_data", "").strip()
    data = data_is_formos(data_tekstas)
    laikas = laikas_is_formos(forma.get("renginio_laikas", "").strip())
    vieta = forma.get("renginio_vieta", "").strip()[:200] or None
    if data_tekstas and data is None:
        return None, None, None, "Neteisinga renginio data."
    if data is None and (laikas or vieta):
        return None, None, None, "Nurodę renginio laiką ar vietą, nurodykite ir datą."
    return data, laikas, vieta, None


@announcements_bp.route("/")
@personalas_required
def saraso():
    kategorija = request.args.get("kategorija", "").strip()
    query = Skelbimas.query
    if kategorija:
        query = query.filter_by(kategorija=kategorija)
    skelbimai = query.order_by(
        Skelbimas.svarbus.desc(), Skelbimas.sukurtas.desc()
    ).all()
    return render_template("announcements/list.html", skelbimai=skelbimai, pasirinkta_kategorija=kategorija)


@announcements_bp.route("/naujas", methods=["GET", "POST"])
@personalas_required
def naujas():
    if request.method == "POST":
        pavadinimas = request.form.get("pavadinimas", "").strip()
        turinys = request.form.get("turinys", "").strip()
        svarbus = request.form.get("svarbus") == "on"
        data, laikas, vieta, klaida = _renginio_laukai(request.form)

        if not pavadinimas or not turinys:
            flash("Pavadinimas ir turinys yra privalomi.", "danger")
        elif klaida:
            flash(klaida, "danger")
        else:
            skelbimas = Skelbimas(
                pavadinimas=pavadinimas,
                turinys=turinys,
                svarbus=svarbus,
                matomas_tevams=request.form.get("matomas_tevams") == "on",
                kategorija=request.form.get("kategorija", "bendra"),
                vartotojo_id=current_user.id,
            )
            db.session.add(skelbimas)
            # BD: pranešimai pagal automatizavimo taisykles – toje pačioje transakcijoje
            skelbti("skelbimas_paskelbtas", skelbimas)
            # BD: nurodžius renginio datą skelbimas atsiranda kalendoriuje
            renginys = susieti_su_kalendoriumi(skelbimas, data, laikas, vieta)
            db.session.commit()
            flash("Skelbimas paskelbtas!" + (" Renginys įtrauktas į kalendorių." if renginys else ""), "success")
            return redirect(url_for("announcements.saraso"))
        return render_template("announcements/form.html", skelbimas=None, forma=request.form)

    return render_template("announcements/form.html", skelbimas=None, forma=None)


@announcements_bp.route("/<int:skelbimo_id>")
@personalas_required
def perziureti(skelbimo_id):
    skelbimas = db.get_or_404(Skelbimas, skelbimo_id)
    return render_template("announcements/detail.html", skelbimas=skelbimas)


@announcements_bp.route("/<int:skelbimo_id>/redaguoti", methods=["GET", "POST"])
@personalas_required
def redaguoti(skelbimo_id):
    skelbimas = db.get_or_404(Skelbimas, skelbimo_id)

    if not current_user.yra_administratorius and skelbimas.vartotojo_id != current_user.id:
        abort(403)

    if request.method == "POST":
        data, laikas, vieta, klaida = _renginio_laukai(request.form)
        pavadinimas = request.form.get("pavadinimas", "").strip()
        turinys = request.form.get("turinys", "").strip()
        if not pavadinimas or not turinys:
            flash("Pavadinimas ir turinys yra privalomi.", "danger")
        elif klaida:
            flash(klaida, "danger")
        else:
            skelbimas.pavadinimas = pavadinimas
            skelbimas.turinys = turinys
            skelbimas.svarbus = request.form.get("svarbus") == "on"
            skelbimas.matomas_tevams = request.form.get("matomas_tevams") == "on"
            skelbimas.kategorija = request.form.get("kategorija", "bendra")
            susieti_su_kalendoriumi(skelbimas, data, laikas, vieta)
            db.session.commit()
            flash("Skelbimas atnaujintas.", "success")
            return redirect(url_for("announcements.perziureti", skelbimo_id=skelbimas.id))
        return render_template("announcements/form.html", skelbimas=skelbimas, forma=request.form)

    return render_template("announcements/form.html", skelbimas=skelbimas, forma=None)


@announcements_bp.route("/<int:skelbimo_id>/salinti", methods=["POST"])
@personalas_required
def salinti(skelbimo_id):
    skelbimas = db.get_or_404(Skelbimas, skelbimo_id)

    if not current_user.yra_administratorius and skelbimas.vartotojo_id != current_user.id:
        abort(403)

    # BD: kartu pašalinamas ir skelbimo renginys kalendoriuje
    pasalinti_rengini(skelbimas)
    db.session.delete(skelbimas)
    db.session.commit()
    flash("Skelbimas pašalintas.", "info")
    return redirect(url_for("announcements.saraso"))
