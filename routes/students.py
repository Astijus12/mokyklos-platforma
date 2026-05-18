"""Mokinių valdymo puslapiai (CRUD - kurti, skaityti, atnaujinti, šalinti)."""
import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required

from models import db, Mokinys, Klase, Pazymys, DALYKAI

students_bp = Blueprint("students", __name__, url_prefix="/mokiniai")


def _parse_data(reiksme):
    if not reiksme:
        return None
    try:
        return datetime.strptime(reiksme, "%Y-%m-%d").date()
    except ValueError:
        return None


@students_bp.route("/")
@login_required
def saraso():
    paieska = request.args.get("paieska", "").strip()
    klases_id = request.args.get("klases_id", type=int)

    query = Mokinys.query
    if paieska:
        like = f"%{paieska}%"
        query = query.filter(
            (Mokinys.vardas.ilike(like)) | (Mokinys.pavarde.ilike(like))
        )
    if klases_id:
        query = query.filter_by(klases_id=klases_id)

    mokiniai = query.order_by(Mokinys.pavarde, Mokinys.vardas).all()
    klases = Klase.query.order_by(Klase.pavadinimas).all()

    return render_template(
        "students/list.html",
        mokiniai=mokiniai,
        klases=klases,
        paieska=paieska,
        pasirinkta_klase=klases_id,
    )


@students_bp.route("/eksportas")
@login_required
def eksportas_csv():
    """Mokinių sąrašo eksportas į CSV failą."""
    klases_id = request.args.get("klases_id", type=int)

    query = Mokinys.query
    if klases_id:
        query = query.filter_by(klases_id=klases_id)

    mokiniai = query.order_by(Mokinys.pavarde, Mokinys.vardas).all()

    output = io.StringIO()
    output.write("﻿")
    rasytojas = csv.writer(output, delimiter=";")
    rasytojas.writerow([
        "Vardas", "Pavardė", "Klasė", "Gimimo data",
        "El. paštas", "Telefonas", "Adresas", "Vidurkis",
    ])

    for m in mokiniai:
        rasytojas.writerow([
            m.vardas,
            m.pavarde,
            m.klase.pavadinimas if m.klase else "",
            m.gimimo_data.strftime("%Y-%m-%d") if m.gimimo_data else "",
            m.email or "",
            m.telefonas or "",
            m.adresas or "",
            m.vidurkis if m.vidurkis else "",
        ])

    failo_vardas = f"mokiniai_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        output.getvalue().encode("utf-8"),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={failo_vardas}"},
    )


@students_bp.route("/<int:mokinio_id>")
@login_required
def detales(mokinio_id):
    """Detalus mokinio puslapis su pažymiais."""
    mokinys = Mokinys.query.get_or_404(mokinio_id)
    pazymiai = (
        Pazymys.query.filter_by(mokinio_id=mokinio_id)
        .order_by(Pazymys.data.desc())
        .all()
    )

    pazymiu_pagal_dalyka = {}
    for p in pazymiai:
        pazymiu_pagal_dalyka.setdefault(p.dalykas, []).append(p)

    dalyku_vidurkiai = []
    for dalykas, pps in pazymiu_pagal_dalyka.items():
        vidurkis = round(sum(p.pazymys for p in pps) / len(pps), 2)
        dalyku_vidurkiai.append({
            "dalykas": dalykas,
            "vidurkis": vidurkis,
            "skaicius": len(pps),
        })
    dalyku_vidurkiai.sort(key=lambda x: x["dalykas"])

    return render_template(
        "students/detail.html",
        mokinys=mokinys,
        pazymiai=pazymiai,
        dalyku_vidurkiai=dalyku_vidurkiai,
    )


@students_bp.route("/naujas", methods=["GET", "POST"])
@login_required
def naujas():
    if request.method == "POST":
        klases_id = request.form.get("klases_id", type=int)
        if not klases_id:
            flash("Pasirinkite klasę.", "danger")
        else:
            mokinys = Mokinys(
                vardas=request.form.get("vardas", "").strip(),
                pavarde=request.form.get("pavarde", "").strip(),
                gimimo_data=_parse_data(request.form.get("gimimo_data")),
                email=request.form.get("email", "").strip() or None,
                telefonas=request.form.get("telefonas", "").strip() or None,
                adresas=request.form.get("adresas", "").strip() or None,
                pastabos=request.form.get("pastabos", "").strip() or None,
                klases_id=klases_id,
            )
            if not mokinys.vardas or not mokinys.pavarde:
                flash("Vardas ir pavardė yra privalomi.", "danger")
            else:
                db.session.add(mokinys)
                db.session.commit()
                flash(f"Mokinys {mokinys.pilnas_vardas} pridėtas.", "success")
                return redirect(url_for("students.detales", mokinio_id=mokinys.id))

    klases = Klase.query.order_by(Klase.pavadinimas).all()
    return render_template(
        "students/form.html",
        mokinys=None,
        klases=klases,
        pradine_klase=request.args.get("klases_id", type=int),
    )


@students_bp.route("/<int:mokinio_id>/redaguoti", methods=["GET", "POST"])
@login_required
def redaguoti(mokinio_id):
    mokinys = Mokinys.query.get_or_404(mokinio_id)

    if request.method == "POST":
        mokinys.vardas = request.form.get("vardas", "").strip()
        mokinys.pavarde = request.form.get("pavarde", "").strip()
        mokinys.gimimo_data = _parse_data(request.form.get("gimimo_data"))
        mokinys.email = request.form.get("email", "").strip() or None
        mokinys.telefonas = request.form.get("telefonas", "").strip() or None
        mokinys.adresas = request.form.get("adresas", "").strip() or None
        mokinys.pastabos = request.form.get("pastabos", "").strip() or None
        mokinys.klases_id = request.form.get("klases_id", type=int)
        db.session.commit()
        flash(f"Mokinio {mokinys.pilnas_vardas} duomenys atnaujinti.", "success")
        return redirect(url_for("students.detales", mokinio_id=mokinys.id))

    klases = Klase.query.order_by(Klase.pavadinimas).all()
    return render_template("students/form.html", mokinys=mokinys, klases=klases)


@students_bp.route("/<int:mokinio_id>/salinti", methods=["POST"])
@login_required
def salinti(mokinio_id):
    mokinys = Mokinys.query.get_or_404(mokinio_id)
    vardas = mokinys.pilnas_vardas
    db.session.delete(mokinys)
    db.session.commit()
    flash(f"Mokinys {vardas} pašalintas.", "info")
    return redirect(url_for("students.saraso"))
