"""Duomenų importo puslapiai (FR-I01–FR-I07). Prieinama tik administratoriui.

Eiga: failo įkėlimas -> peržiūra (aprašo 14 pav. maketas) -> patvirtinimas
(viena transakcija) -> ataskaita, kurią galima atsisiųsti CSV formatu.
"""
from datetime import datetime

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user

from models import ImportoEilute, ImportoSesija, db
from routes.audit import registruoti
from routes.auth import admin_required
from services.importas import (
    DIDZIAUSIAS_EILUCIU_SK,
    ImportoKlaida,
    ImportoVykdytojas,
    SABLONO_STULPELIAI,
    ataskaitos_csv,
    sablono_xlsx,
)

importas_bp = Blueprint("importas", __name__, url_prefix="/importas")


@importas_bp.route("/", methods=["GET", "POST"])
@admin_required
def ikelimas():
    if request.method == "POST":
        failas = request.files.get("failas")
        if failas is None or not failas.filename:
            flash("Pasirinkite XLSX arba CSV failą.", "danger")
        else:
            vykdytojas = ImportoVykdytojas()
            try:
                sesija = vykdytojas.nuskaityti(failas.filename, failas.read(), current_user)
                vykdytojas.tikrinti(sesija)
                db.session.commit()
            except ImportoKlaida as klaida:
                db.session.rollback()
                flash(str(klaida), "danger")
            else:
                registruoti("importas_ikeltas", "importo_sesija", sesija.id, sesija.failo_vardas)
                return redirect(url_for("importas.perziura", sesijos_id=sesija.id))
    sesijos = ImportoSesija.query.order_by(ImportoSesija.sukurta.desc()).limit(20).all()
    return render_template("importas/ikelimas.html", sesijos=sesijos, stulpeliai=SABLONO_STULPELIAI,
                           didziausias=DIDZIAUSIAS_EILUCIU_SK)


@importas_bp.route("/sablonas.xlsx")
@admin_required
def sablonas():
    return Response(sablono_xlsx(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=mokiniu_importo_sablonas.xlsx"})


@importas_bp.route("/<int:sesijos_id>/perziura")
@admin_required
def perziura(sesijos_id):
    """FR-I04: tinkamos, klaidingos ir pasikartojančios eilutės prieš įrašant."""
    sesija = db.get_or_404(ImportoSesija, sesijos_id)
    if sesija.busena != ImportoSesija.PATIKRINTA:
        return redirect(url_for("importas.ataskaita", sesijos_id=sesija.id))
    rodyti_visas = request.args.get("rodyti") == "visas"
    problemines = [e for e in sesija.eilutes if e.busena in (ImportoEilute.KLAIDA, ImportoEilute.DUBLIKATAS)]
    return render_template("importas/perziura.html", sesija=sesija, rodyti_visas=rodyti_visas,
                           problemines=problemines, eilutes=sesija.eilutes if rodyti_visas else problemines,
                           dublikatu=sum(1 for e in sesija.eilutes if e.busena == ImportoEilute.DUBLIKATAS))


@importas_bp.route("/<int:sesijos_id>/patvirtinti", methods=["POST"])
@admin_required
def patvirtinti(sesijos_id):
    """FR-I05, FR-I06: tinkamos eilutės, tėvų paskyros ir kvietimai – viena transakcija."""
    sesija = db.get_or_404(ImportoSesija, sesijos_id)
    try:
        sesija = ImportoVykdytojas().irasyti(sesija, current_user)
    except ImportoKlaida as klaida:
        flash(str(klaida), "warning")
    except Exception:
        flash("Importuoti nepavyko – neįrašyta nė viena eilutė. Bandykite dar kartą.", "danger")
    else:
        irasyta = sum(1 for e in sesija.eilutes if e.busena == ImportoEilute.IRASYTA)
        registruoti("importas_baigtas", "importo_sesija", sesija.id, f"Įrašyta mokinių: {irasyta}")
        flash(f"Importas baigtas: įrašyta {irasyta} mokinių.", "success")
    return redirect(url_for("importas.ataskaita", sesijos_id=sesijos_id))


@importas_bp.route("/<int:sesijos_id>/atsaukti", methods=["POST"])
@admin_required
def atsaukti(sesijos_id):
    sesija = db.get_or_404(ImportoSesija, sesijos_id)
    if sesija.busena == ImportoSesija.PATIKRINTA:
        sesija.busena = ImportoSesija.ATSAUKTA
        db.session.commit()
        flash("Importas atšauktas, duomenys neįrašyti.", "info")
    return redirect(url_for("importas.ikelimas"))


@importas_bp.route("/<int:sesijos_id>/ataskaita")
@admin_required
def ataskaita(sesijos_id):
    """FR-I07: įrašytos ir praleistos eilutės su priežastimis."""
    sesija = db.get_or_404(ImportoSesija, sesijos_id)
    kiekiai = {busena: sum(1 for e in sesija.eilutes if e.busena == busena) for busena in ImportoEilute.BUSENOS}
    return render_template("importas/ataskaita.html", sesija=sesija, kiekiai=kiekiai)


@importas_bp.route("/<int:sesijos_id>/ataskaita.csv")
@admin_required
def ataskaita_csv(sesijos_id):
    sesija = db.get_or_404(ImportoSesija, sesijos_id)
    pavadinimas = f"importo_ataskaita_{sesija.id}_{datetime.now():%Y%m%d}.csv"
    return Response(ataskaitos_csv(sesija).encode("utf-8"), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={pavadinimas}"})
