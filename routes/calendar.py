"""Mokyklos renginių kalendorius."""
from datetime import datetime, date, timedelta
from calendar import monthrange
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required

from models import db, Renginys
from routes.auth import personalas_required, admin_required

calendar_bp = Blueprint("calendar", __name__, url_prefix="/kalendorius")


def _parse_data(reiksme):
    if not reiksme:
        return None
    try:
        return datetime.strptime(reiksme, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_laikas(reiksme):
    if not reiksme:
        return None
    try:
        return datetime.strptime(reiksme, "%H:%M").time()
    except ValueError:
        return None


@calendar_bp.route("/")
@login_required
def rodinys():
    """Kalendoriaus pagrindinis puslapis - mėnesio rodinys."""
    metai = request.args.get("metai", type=int) or date.today().year
    menuo = request.args.get("menuo", type=int) or date.today().month

    if menuo < 1:
        menuo = 12
        metai -= 1
    elif menuo > 12:
        menuo = 1
        metai += 1

    pradzia = date(metai, menuo, 1)
    dienu_menesyje = monthrange(metai, menuo)[1]
    pabaiga = date(metai, menuo, dienu_menesyje)

    query = Renginys.query.filter(
        Renginys.pradzios_data >= pradzia,
        Renginys.pradzios_data <= pabaiga,
    )

    if current_user.yra_tevas:
        query = query.filter_by(matomas_tevams=True)

    renginiai = query.order_by(Renginys.pradzios_data, Renginys.pradzios_laikas).all()

    renginiai_pagal_diena = {}
    for r in renginiai:
        raktas = r.pradzios_data.isoformat()
        renginiai_pagal_diena.setdefault(raktas, []).append(r)

    savaites_dienos = ["Pir", "Ant", "Tre", "Ket", "Pen", "Šeš", "Sek"]

    pirma_savaite = pradzia.weekday()
    tinklas = []
    diena = 1

    for i in range(pirma_savaite):
        tinklas.append(None)

    while diena <= dienu_menesyje:
        d = date(metai, menuo, diena)
        tinklas.append({
            "data": d,
            "renginiai": renginiai_pagal_diena.get(d.isoformat(), []),
            "siandien": d == date.today(),
        })
        diena += 1

    while len(tinklas) % 7 != 0:
        tinklas.append(None)

    menesio_pavadinimas = [
        "Sausis", "Vasaris", "Kovas", "Balandis", "Gegužė", "Birželis",
        "Liepa", "Rugpjūtis", "Rugsėjis", "Spalis", "Lapkritis", "Gruodis"
    ][menuo - 1]

    prev_menuo = menuo - 1 if menuo > 1 else 12
    prev_metai = metai if menuo > 1 else metai - 1
    next_menuo = menuo + 1 if menuo < 12 else 1
    next_metai = metai if menuo < 12 else metai + 1

    return render_template(
        "calendar/rodinys.html",
        menesio_pavadinimas=menesio_pavadinimas,
        metai=metai,
        menuo=menuo,
        prev_metai=prev_metai,
        prev_menuo=prev_menuo,
        next_metai=next_metai,
        next_menuo=next_menuo,
        savaites_dienos=savaites_dienos,
        tinklas=tinklas,
        siandien=date.today(),
    )


@calendar_bp.route("/naujas", methods=["GET", "POST"])
@personalas_required
def naujas():
    """Naujo renginio kūrimas."""
    if request.method == "POST":
        pavadinimas = request.form.get("pavadinimas", "").strip()
        pradzios_data = _parse_data(request.form.get("pradzios_data"))

        if not pavadinimas or not pradzios_data:
            flash("Pavadinimas ir pradžios data yra privalomi.", "danger")
        else:
            r = Renginys(
                pavadinimas=pavadinimas,
                aprasymas=request.form.get("aprasymas", "").strip() or None,
                pradzios_data=pradzios_data,
                pradzios_laikas=_parse_laikas(request.form.get("pradzios_laikas")),
                pabaigos_data=_parse_data(request.form.get("pabaigos_data")),
                pabaigos_laikas=_parse_laikas(request.form.get("pabaigos_laikas")),
                vieta=request.form.get("vieta", "").strip() or None,
                kategorija=request.form.get("kategorija", "mokyklos"),
                matomas_tevams=request.form.get("matomas_tevams") == "on",
                vartotojo_id=current_user.id,
            )
            db.session.add(r)
            db.session.commit()

            try:
                from routes.audit import registruoti
                registruoti("sukurta", "renginys", r.id, f"Sukurtas renginys: {r.pavadinimas}")
            except Exception:
                pass

            flash(f"Renginys '{r.pavadinimas}' sukurtas.", "success")
            return redirect(url_for("calendar.rodinys"))

    return render_template("calendar/forma.html", renginys=None)


@calendar_bp.route("/<int:renginio_id>")
@login_required
def perziureti(renginio_id):
    r = Renginys.query.get_or_404(renginio_id)
    if current_user.yra_tevas and not r.matomas_tevams:
        abort(403)
    return render_template("calendar/detales.html", renginys=r)


@calendar_bp.route("/<int:renginio_id>/salinti", methods=["POST"])
@personalas_required
def salinti(renginio_id):
    r = Renginys.query.get_or_404(renginio_id)
    if not current_user.yra_administratorius and r.vartotojo_id != current_user.id:
        abort(403)

    vardas = r.pavadinimas
    db.session.delete(r)
    db.session.commit()
    flash(f"Renginys '{vardas}' pašalintas.", "info")
    return redirect(url_for("calendar.rodinys"))
