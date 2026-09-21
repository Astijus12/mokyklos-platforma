"""Mokinių valdymo puslapiai (CRUD - kurti, skaityti, atnaujinti, šalinti)."""
import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required
from routes.auth import personalas_required

from models import db, Mokinys, Klase

students_bp = Blueprint("students", __name__, url_prefix="/mokiniai")


def _parse_data(reiksme):
    if not reiksme:
        return None
    try:
        return datetime.strptime(reiksme, "%Y-%m-%d").date()
    except ValueError:
        return None


def _surinkti_duomenis(form):
    """Iš formos duomenų sukuria/atnaujina mokinio duomenis."""
    return {
        "vardas": form.get("vardas", "").strip(),
        "pavarde": form.get("pavarde", "").strip(),
        "gimimo_data": _parse_data(form.get("gimimo_data")),
        "email": form.get("email", "").strip() or None,
        "telefonas": form.get("telefonas", "").strip() or None,
        "adresas": form.get("adresas", "").strip() or None,
        "pastabos": form.get("pastabos", "").strip() or None,
        "motinos_vardas": form.get("motinos_vardas", "").strip() or None,
        "motinos_telefonas": form.get("motinos_telefonas", "").strip() or None,
        "motinos_email": form.get("motinos_email", "").strip() or None,
        "tevo_vardas": form.get("tevo_vardas", "").strip() or None,
        "tevo_telefonas": form.get("tevo_telefonas", "").strip() or None,
        "tevo_email": form.get("tevo_email", "").strip() or None,
        "mokyklos_autobusas": form.get("mokyklos_autobusas") == "on",
        "geroves_komisija": form.get("geroves_komisija") == "on",
        "geroves_komisija_data": _parse_data(form.get("geroves_komisija_data")) if form.get("geroves_komisija") == "on" else None,
        "geroves_komisija_pastabos": form.get("geroves_komisija_pastabos", "").strip() or None if form.get("geroves_komisija") == "on" else None,
    }


@students_bp.route("/")
@personalas_required
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
@personalas_required
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
        "El. paštas", "Telefonas", "Adresas",
        "Motinos vardas", "Motinos telefonas", "Motinos el. paštas",
        "Tėvo vardas", "Tėvo telefonas", "Tėvo el. paštas",
        "Mokyklos autobusas", "Gerovės komisija", "Gerovės kom. data",
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
            m.motinos_vardas or "",
            m.motinos_telefonas or "",
            m.motinos_email or "",
            m.tevo_vardas or "",
            m.tevo_telefonas or "",
            m.tevo_email or "",
            "Taip" if m.mokyklos_autobusas else "Ne",
            "Taip" if m.geroves_komisija else "Ne",
            m.geroves_komisija_data.strftime("%Y-%m-%d") if m.geroves_komisija_data else "",
        ])

    failo_vardas = f"mokiniai_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        output.getvalue().encode("utf-8"),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={failo_vardas}"},
    )


@students_bp.route("/<int:mokinio_id>")
@personalas_required
def detales(mokinio_id):
    """Detalus mokinio puslapis."""
    mokinys = Mokinys.query.get_or_404(mokinio_id)
    return render_template("students/detail.html", mokinys=mokinys)


@students_bp.route("/naujas", methods=["GET", "POST"])
@personalas_required
def naujas():
    if request.method == "POST":
        klases_id = request.form.get("klases_id", type=int)
        if not klases_id:
            flash("Pasirinkite klasę.", "danger")
        else:
            duomenys = _surinkti_duomenis(request.form)
            duomenys["klases_id"] = klases_id

            if not duomenys["vardas"] or not duomenys["pavarde"]:
                flash("Vardas ir pavardė yra privalomi.", "danger")
            else:
                mokinys = Mokinys(**duomenys)
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
@personalas_required
def redaguoti(mokinio_id):
    mokinys = Mokinys.query.get_or_404(mokinio_id)

    if request.method == "POST":
        duomenys = _surinkti_duomenis(request.form)
        for laukas, reiksme in duomenys.items():
            setattr(mokinys, laukas, reiksme)
        mokinys.klases_id = request.form.get("klases_id", type=int)
        db.session.commit()
        flash(f"Mokinio {mokinys.pilnas_vardas} duomenys atnaujinti.", "success")
        return redirect(url_for("students.detales", mokinio_id=mokinys.id))

    klases = Klase.query.order_by(Klase.pavadinimas).all()
    return render_template("students/form.html", mokinys=mokinys, klases=klases)


@students_bp.route("/<int:mokinio_id>/salinti", methods=["POST"])
@personalas_required
def salinti(mokinio_id):
    mokinys = Mokinys.query.get_or_404(mokinio_id)
    vardas = mokinys.pilnas_vardas
    db.session.delete(mokinys)
    db.session.commit()
    flash(f"Mokinys {vardas} pašalintas.", "info")
    return redirect(url_for("students.saraso"))
