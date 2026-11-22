"""Dokumentų modulio puslapiai (FR-D01–FR-D08).

Administratoriui: dokumentų registras su paieška ir vientisumo patikra, pažymų
prašymų nagrinėjimas, ataskaita už pasirinktą laikotarpį. Tėvui: pažymų užsakymas
ir ankstesnių prašymų sąrašas (aprašo 16 pav. maketas). Atsisiųsti dokumentą gali
tik tas, kam jis skirtas (services/pazymos.py gali_atsisiusti).
"""
import os
from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from models import Dokumentas, Mokinys, PazymosPrasymas, db
from routes.audit import registruoti
from routes.auth import admin_required, tevas_required
from services.dokumentai import kelias_diske, tikrinti_vientisuma
from services.pazymos import (
    PASKIRTYS,
    PrasymoKlaida,
    ankstesnis_menuo,
    atmesti_prasyma,
    gali_atsisiusti,
    parengti_ataskaita,
    pateikti_prasyma,
    patvirtinti_prasyma,
)

dokumentai_bp = Blueprint("dokumentai", __name__, url_prefix="/dokumentai")

REGISTRO_PUSLAPIO_DYDIS = 50


def _data(reiksme):
    try:
        return datetime.strptime(reiksme, "%Y-%m-%d").date() if reiksme else None
    except ValueError:
        return None


# --- Dokumentų registras (FR-D08) -------------------------------------------------

@dokumentai_bp.route("/")
@admin_required
def registras():
    pasirinkti = {
        "numeris": request.args.get("numeris", "").strip(),
        "tipas": request.args.get("tipas", ""),
        "mokinys": request.args.get("mokinys", "").strip(),
        "nuo": request.args.get("nuo", ""),
        "iki": request.args.get("iki", ""),
    }
    uzklausa = Dokumentas.query.outerjoin(Mokinys, Dokumentas.mokinio_id == Mokinys.id)
    if pasirinkti["numeris"]:
        uzklausa = uzklausa.filter(Dokumentas.numeris.ilike(f"%{pasirinkti['numeris']}%"))
    if pasirinkti["tipas"] in Dokumentas.TIPAI:
        uzklausa = uzklausa.filter(Dokumentas.tipas == pasirinkti["tipas"])
    if pasirinkti["mokinys"]:
        sablonas = f"%{pasirinkti['mokinys']}%"
        uzklausa = uzklausa.filter(or_(Mokinys.vardas.ilike(sablonas), Mokinys.pavarde.ilike(sablonas)))
    if _data(pasirinkti["nuo"]):
        uzklausa = uzklausa.filter(Dokumentas.sukurta >= datetime.combine(_data(pasirinkti["nuo"]),
                                                                          datetime.min.time()))
    if _data(pasirinkti["iki"]):
        uzklausa = uzklausa.filter(Dokumentas.sukurta < datetime.combine(_data(pasirinkti["iki"]),
                                                                         datetime.max.time()))
    dokumentai = uzklausa.order_by(Dokumentas.sukurta.desc(), Dokumentas.id.desc()).paginate(
        page=request.args.get("puslapis", 1, type=int), per_page=REGISTRO_PUSLAPIO_DYDIS, error_out=False)
    return render_template("dokumentai/registras.html", dokumentai=dokumentai, pasirinkti=pasirinkti,
                           tipai=Dokumentas.TIPAI,
                           laukia_prasymu=PazymosPrasymas.query.filter_by(busena=PazymosPrasymas.PATEIKTAS).count())


@dokumentai_bp.route("/<int:dokumento_id>/atsisiusti")
@login_required
def atsisiusti(dokumento_id):
    dokumentas = db.get_or_404(Dokumentas, dokumento_id)
    # Kitam naudotojui atsakoma 404, kad nebūtų galima sužinoti, ar toks dokumentas yra
    if not gali_atsisiusti(current_user, dokumentas):
        abort(404)
    kelias = kelias_diske(dokumentas)
    if not os.path.exists(kelias):
        abort(404)
    registruoti("dokumentas_atsisiustas", "dokumentas", dokumentas.id, dokumentas.numeris)
    return send_file(kelias, mimetype="application/pdf", as_attachment=True,
                     download_name=f"{dokumentas.numeris}.pdf")


@dokumentai_bp.route("/<int:dokumento_id>/tikrinti", methods=["POST"])
@admin_required
def tikrinti(dokumento_id):
    """FR-D05: ar failas nepakeistas po sugeneravimo (SHA-256 palyginimas)."""
    dokumentas = db.get_or_404(Dokumentas, dokumento_id)
    if tikrinti_vientisuma(dokumentas):
        flash(f"Dokumentas {dokumentas.numeris} nepakeistas: kontrolinė suma sutampa.", "success")
    else:
        flash(f"Dėmesio: dokumento {dokumentas.numeris} failas pakeistas arba nerastas.", "danger")
    return redirect(request.referrer or url_for("dokumentai.registras"))


# --- Pažymų prašymai: administratorius (FR-D02, FR-D03) --------------------------

@dokumentai_bp.route("/prasymai")
@admin_required
def prasymai():
    visi = (PazymosPrasymas.query
            .order_by((PazymosPrasymas.busena == PazymosPrasymas.PATEIKTAS).desc(),
                      PazymosPrasymas.pateikta.desc())
            .all())
    return render_template("dokumentai/prasymai.html", prasymai=visi)


@dokumentai_bp.route("/prasymai/<int:prasymo_id>/patvirtinti", methods=["POST"])
@admin_required
def patvirtinti(prasymo_id):
    prasymas = db.get_or_404(PazymosPrasymas, prasymo_id)
    try:
        dokumentas = patvirtinti_prasyma(prasymas, current_user)
    except PrasymoKlaida as klaida:
        db.session.rollback()
        flash(str(klaida), "warning")
    else:
        registruoti("pazyma_parengta", "dokumentas", dokumentas.id, dokumentas.numeris)
        flash(f"Pažyma {dokumentas.numeris} parengta, tėvui išsiųstas pranešimas.", "success")
    return redirect(url_for("dokumentai.prasymai"))


@dokumentai_bp.route("/prasymai/<int:prasymo_id>/atmesti", methods=["POST"])
@admin_required
def atmesti(prasymo_id):
    prasymas = db.get_or_404(PazymosPrasymas, prasymo_id)
    try:
        atmesti_prasyma(prasymas, current_user, request.form.get("priezastis"))
    except PrasymoKlaida as klaida:
        db.session.rollback()
        flash(str(klaida), "danger")
    else:
        registruoti("pazymos_prasymas_atmestas", "pazymos_prasymas", prasymas.id, prasymas.paskirtis)
        flash("Prašymas atmestas, tėvui išsiųstas pranešimas su priežastimi.", "info")
    return redirect(url_for("dokumentai.prasymai"))


# --- Ataskaita už laikotarpį (FR-D07) -----------------------------------------------

@dokumentai_bp.route("/ataskaita", methods=["GET", "POST"])
@admin_required
def ataskaita():
    numatytasis_nuo, numatytasis_iki = ankstesnis_menuo(date.today())
    if request.method == "POST":
        nuo, iki = _data(request.form.get("nuo")), _data(request.form.get("iki"))
        if not nuo or not iki:
            flash("Nurodykite laikotarpio pradžią ir pabaigą.", "danger")
        else:
            try:
                dokumentas = parengti_ataskaita(nuo, iki, sukure=current_user)
            except PrasymoKlaida as klaida:
                flash(str(klaida), "danger")
            else:
                registruoti("ataskaita_parengta", "dokumentas", dokumentas.id, dokumentas.numeris)
                flash(f"Ataskaita {dokumentas.numeris} parengta.", "success")
                return redirect(url_for("dokumentai.registras", tipas="AT"))
    return render_template("dokumentai/ataskaita.html", nuo=numatytasis_nuo, iki=numatytasis_iki)


# --- Tėvų portalas: pažymų užsakymas (FR-D01) ----------------------------------------

@dokumentai_bp.route("/mano-pazymos", methods=["GET", "POST"])
@tevas_required
def mano_pazymos():
    vaikai = current_user.vaikai.order_by(Mokinys.vardas).all()
    if request.method == "POST":
        mokinys = db.session.get(Mokinys, request.form.get("mokinio_id", type=int) or 0)
        try:
            pateikti_prasyma(current_user, mokinys, request.form.get("paskirtis"),
                             request.form.get("papildoma", ""))
        except PrasymoKlaida as klaida:
            db.session.rollback()
            flash(str(klaida), "danger")
        else:
            flash("Prašymas pateiktas. Apie parengtą pažymą jums bus pranešta.", "success")
            return redirect(url_for("dokumentai.mano_pazymos"))

    prasymai = (PazymosPrasymas.query.filter_by(tevo_id=current_user.id)
                .order_by(PazymosPrasymas.pateikta.desc()).all())
    return render_template("dokumentai/mano_pazymos.html", vaikai=vaikai, prasymai=prasymai,
                           paskirtys=PASKIRTYS)
