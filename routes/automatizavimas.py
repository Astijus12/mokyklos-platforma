"""Automatizavimo modulio puslapiai (FR-A01, FR-A03, FR-A07, FR-A09).

Administratoriui: taisyklių sąrašas su jungikliais ir paskutinės paros siuntimo
suvestine (aprašo 15 pav. maketas), taisyklių ir šablonų redagavimas, siuntimo
žurnalas su pakartotinio siuntimo veiksmu. Visiems prisijungusiems – asmeniniai
pranešimų nustatymai.

Maršrutai tik priima duomenis, juos patikrina ir parodo rezultatą; pranešimų
kūrimo ir siuntimo logika yra paslaugų sluoksnyje (services/).
"""
import json
import re
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from models import (
    AutomatizavimoTaisykle,
    EilesIrasas,
    PranesimoSablonas,
    PranesimuNustatymas,
    User,
    db,
    utc_dabar,
)
from models.automatizavimas import KANALAI
from routes.audit import registruoti
from routes.auth import admin_required
from services.eile import PranesimuEile
from services.ivykiai import IVYKIU_TIPAI, rodomas_nustatymuose
from services.sablonai import PAVYZDINIAI_DUOMENYS, SablonoKlaida, SablonuApdorotojas
from services.taisykles import GAVEJU_GRUPES, patikrinti_salyga

automatizavimas_bp = Blueprint("automatizavimas", __name__, url_prefix="/automatizavimas")

ZURNALO_PUSLAPIO_DYDIS = 50
DIDZIAUSIAS_POSLINKIS = 60
VIETINE_JUOSTA = ZoneInfo("Europe/Vilnius")
KODO_FORMATAS = re.compile(r"^[a-z][a-z0-9_]{1,49}$")

# Priminimų taisyklių aprašymui sąraše, pvz., „1 diena iki renginio“
_PRIMINIMO_OBJEKTAS = {
    "renginys_artejantis": "renginio",
    "vgk_posedis_artejantis": "posėdžio",
    "priemones_terminas_artejantis": "termino",
}


@automatizavimas_bp.app_template_filter("vietinis_laikas")
def vietinis_laikas(utc_laikas):
    """Duomenų bazėje laikas saugomas UTC – puslapyje rodomas Lietuvos laikas."""
    if utc_laikas is None:
        return ""
    return utc_laikas.replace(tzinfo=timezone.utc).astimezone(VIETINE_JUOSTA).strftime("%Y-%m-%d %H:%M")


@automatizavimas_bp.app_template_filter("lt_forma")
def lt_forma(skaicius, vienaskaita, daugiskaita, kilmininkas):
    """Lietuviška žodžio forma pagal skaičių: 1 diena, 2 dienos, 10 dienų, 21 diena."""
    if skaicius % 10 == 1 and skaicius % 100 != 11:
        return vienaskaita
    if 2 <= skaicius % 10 <= 9 and not 12 <= skaicius % 100 <= 19:
        return daugiskaita
    return kilmininkas


def dienu_zodis(skaicius):
    return lt_forma(skaicius, "diena", "dienos", "dienų")


def ivykio_aprasymas(taisykle):
    """Stulpelis „Įvykis“: priminimams nurodomas poslinkis, kaip makete."""
    if taisykle.ivykio_tipas == "menesio_suvestine":
        return "Kiekvieno mėnesio 1 d."
    tipas = IVYKIU_TIPAI.get(taisykle.ivykio_tipas)
    if tipas is None:
        return taisykle.ivykio_tipas
    if tipas.priminimas:
        n = taisykle.poslinkis_d
        if n == 0:
            return f"{tipas.pavadinimas} (tą pačią dieną)"
        darbo = "darbo " if tipas.darbo_dienomis else ""
        return f"{n} {darbo}{dienu_zodis(n)} iki {_PRIMINIMO_OBJEKTAS.get(tipas.kodas, 'datos')}"
    return tipas.pavadinimas


def gaveju_pavadinimas(kodas):
    grupe = GAVEJU_GRUPES.get(kodas)
    return grupe.pavadinimas if grupe else kodas


# --- Taisyklės (FR-A01) ---------------------------------------------------------------

@automatizavimas_bp.route("/")
@admin_required
def taisykles():
    visos = AutomatizavimoTaisykle.query.order_by(AutomatizavimoTaisykle.id).all()
    eilutes = [{
        "taisykle": t,
        "ivykis": ivykio_aprasymas(t),
        "gavejai": gaveju_pavadinimas(t.gavejai),
        "kanalai": [(k, KANALAI.get(k, k)) for k in t.kanalu_sarasas],
    } for t in visos]
    statistika = PranesimuEile().statistika(utc_dabar() - timedelta(hours=24))
    return render_template(
        "automatizavimas/taisykles.html",
        eilutes=eilutes,
        aktyviu=sum(1 for t in visos if t.aktyvi),
        statistika=statistika,
    )


@automatizavimas_bp.route("/taisykles/<int:taisykles_id>/perjungti", methods=["POST"])
@admin_required
def perjungti(taisykles_id):
    """Taisyklės įjungimas arba išjungimas vienu paspaudimu."""
    taisykle = db.get_or_404(AutomatizavimoTaisykle, taisykles_id)
    taisykle.aktyvi = not taisykle.aktyvi
    db.session.commit()
    registruoti("taisykle_ijungta" if taisykle.aktyvi else "taisykle_isjungta",
                "automatizavimo_taisykle", taisykle.id, taisykle.pavadinimas)

    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"aktyvi": taisykle.aktyvi})
    busena = "įjungta" if taisykle.aktyvi else "išjungta"
    flash(f"Taisyklė „{taisykle.pavadinimas}“ {busena}.", "success")
    return redirect(url_for("automatizavimas.taisykles"))


def _taisykles_duomenys(forma):
    """Surenka ir patikrina taisyklės formos duomenis. Grąžina (duomenys, klaidos)."""
    klaidos = []
    tipas = IVYKIU_TIPAI.get(forma.get("ivykio_tipas", ""))
    duomenys = {
        "pavadinimas": forma.get("pavadinimas", "").strip(),
        "ivykio_tipas": forma.get("ivykio_tipas", ""),
        "gavejai": forma.get("gavejai", ""),
        "kanalas": ",".join(k for k in KANALAI if k in forma.getlist("kanalai")),
        "sablono_id": forma.get("sablono_id", type=int),
        "poslinkis_d": forma.get("poslinkis_d", default=0, type=int) or 0,
        "aktyvi": forma.get("aktyvi") == "on",
        "salyga": None,
    }

    if not duomenys["pavadinimas"]:
        klaidos.append("Nurodykite taisyklės pavadinimą.")
    if tipas is None:
        klaidos.append("Pasirinkite įvykį.")
    elif duomenys["gavejai"] not in tipas.gavejai:
        klaidos.append("Pasirinkta gavėjų grupė šiam įvykiui netinka.")
    if not duomenys["kanalas"]:
        klaidos.append("Pasirinkite bent vieną kanalą.")
    if duomenys["sablono_id"] is None or db.session.get(PranesimoSablonas, duomenys["sablono_id"]) is None:
        klaidos.append("Pasirinkite pranešimo šabloną.")

    if tipas is not None and tipas.priminimas:
        if not 0 <= duomenys["poslinkis_d"] <= DIDZIAUSIAS_POSLINKIS:
            klaidos.append(f"Poslinkis turi būti nuo 0 iki {DIDZIAUSIAS_POSLINKIS} dienų.")
    else:
        duomenys["poslinkis_d"] = 0

    salygos_tekstas = forma.get("salyga", "").strip()
    if salygos_tekstas:
        try:
            duomenys["salyga"] = json.loads(salygos_tekstas)
        except json.JSONDecodeError:
            klaidos.append("Sąlyga turi būti teisingas JSON, pvz., {\"matomas_tevams\": true}.")
        else:
            klaida = patikrinti_salyga(duomenys["salyga"])
            if klaida:
                klaidos.append(klaida)
    return duomenys, klaidos


@automatizavimas_bp.route("/taisykles/nauja", methods=["GET", "POST"])
@automatizavimas_bp.route("/taisykles/<int:taisykles_id>/redaguoti", methods=["GET", "POST"])
@admin_required
def taisykles_forma(taisykles_id=None):
    taisykle = db.get_or_404(AutomatizavimoTaisykle, taisykles_id) if taisykles_id else None
    salygos_tekstas = json.dumps(taisykle.salyga, ensure_ascii=False) if taisykle and taisykle.salyga else ""

    if request.method == "POST":
        duomenys, klaidos = _taisykles_duomenys(request.form)
        salygos_tekstas = request.form.get("salyga", "").strip()
        if klaidos:
            for klaida in klaidos:
                flash(klaida, "danger")
        else:
            nauja = taisykle is None
            if nauja:
                taisykle = AutomatizavimoTaisykle()
                db.session.add(taisykle)
            for laukas, reiksme in duomenys.items():
                setattr(taisykle, laukas, reiksme)
            db.session.commit()
            registruoti("taisykle_sukurta" if nauja else "taisykle_pakeista",
                        "automatizavimo_taisykle", taisykle.id, taisykle.pavadinimas)
            flash(f"Taisyklė „{taisykle.pavadinimas}“ išsaugota.", "success")
            return redirect(url_for("automatizavimas.taisykles"))

    return render_template(
        "automatizavimas/taisykle_forma.html",
        taisykle=taisykle,
        forma=request.form if request.method == "POST" else None,
        salygos_tekstas=salygos_tekstas,
        ivykiu_tipai=IVYKIU_TIPAI,
        gaveju_grupes=GAVEJU_GRUPES,
        kanalai=KANALAI,
        sablonai=PranesimoSablonas.query.order_by(PranesimoSablonas.pavadinimas).all(),
        didziausias_poslinkis=DIDZIAUSIAS_POSLINKIS,
    )


@automatizavimas_bp.route("/taisykles/<int:taisykles_id>/salinti", methods=["POST"])
@admin_required
def salinti_taisykle(taisykles_id):
    taisykle = db.get_or_404(AutomatizavimoTaisykle, taisykles_id)
    pavadinimas = taisykle.pavadinimas
    db.session.delete(taisykle)  # eilės įrašai lieka žurnale (taisykles_id tampa NULL)
    db.session.commit()
    registruoti("taisykle_pasalinta", "automatizavimo_taisykle", taisykles_id, pavadinimas)
    flash(f"Taisyklė „{pavadinimas}“ pašalinta.", "info")
    return redirect(url_for("automatizavimas.taisykles"))


# --- Šablonai (FR-A03) ---------------------------------------------------------------

@automatizavimas_bp.route("/sablonai")
@admin_required
def sablonai():
    visi = PranesimoSablonas.query.order_by(PranesimoSablonas.pavadinimas).all()
    return render_template("automatizavimas/sablonai.html", sablonai=visi)


def _sablono_duomenys(forma, sablonas):
    duomenys = {
        "kodas": forma.get("kodas", "").strip().lower(),
        "pavadinimas": forma.get("pavadinimas", "").strip(),
        "tema": forma.get("tema", "").strip(),
        "tekstas": forma.get("tekstas", "").replace("\r\n", "\n").strip(),
    }
    klaidos = []
    if not KODO_FORMATAS.match(duomenys["kodas"]):
        klaidos.append("Kodas – 2–50 mažųjų lotyniškų raidžių, skaitmenų ar pabraukimų, pradedant raide.")
    else:
        kitas = PranesimoSablonas.query.filter_by(kodas=duomenys["kodas"]).first()
        if kitas is not None and kitas is not sablonas:
            klaidos.append("Šablonas tokiu kodu jau yra.")
    if not duomenys["pavadinimas"] or not duomenys["tema"] or not duomenys["tekstas"]:
        klaidos.append("Pavadinimas, tema ir tekstas yra privalomi.")
    else:
        klaida = SablonuApdorotojas().patikrinti(PranesimoSablonas(tema=duomenys["tema"],
                                                                   tekstas=duomenys["tekstas"]))
        if klaida:
            klaidos.append(f"Šablono klaida: {klaida}")
    return duomenys, klaidos


@automatizavimas_bp.route("/sablonai/naujas", methods=["GET", "POST"])
@automatizavimas_bp.route("/sablonai/<int:sablono_id>/redaguoti", methods=["GET", "POST"])
@admin_required
def sablono_forma(sablono_id=None):
    sablonas = db.get_or_404(PranesimoSablonas, sablono_id) if sablono_id else None

    if request.method == "POST":
        duomenys, klaidos = _sablono_duomenys(request.form, sablonas)
        if klaidos:
            for klaida in klaidos:
                flash(klaida, "danger")
        else:
            naujas = sablonas is None
            if naujas:
                sablonas = PranesimoSablonas()
                db.session.add(sablonas)
            for laukas, reiksme in duomenys.items():
                setattr(sablonas, laukas, reiksme)
            db.session.commit()
            registruoti("sablonas_sukurtas" if naujas else "sablonas_pakeistas",
                        "pranesimu_sablonas", sablonas.id, sablonas.pavadinimas)
            flash(f"Šablonas „{sablonas.pavadinimas}“ išsaugotas.", "success")
            return redirect(url_for("automatizavimas.sablonai"))

    return render_template(
        "automatizavimas/sablonas_forma.html",
        sablonas=sablonas,
        forma=request.form if request.method == "POST" else None,
        kintamieji=PAVYZDINIAI_DUOMENYS,
    )


@automatizavimas_bp.route("/sablonai/perziura", methods=["POST"])
@admin_required
def sablono_perziura():
    """Šablono peržiūra su pavyzdiniais duomenimis (formoje, prieš išsaugant)."""
    juodrastis = PranesimoSablonas(tema=request.form.get("tema", ""),
                                   tekstas=request.form.get("tekstas", "").replace("\r\n", "\n"))
    try:
        tema, tekstas = SablonuApdorotojas().perziura(juodrastis)
    except SablonoKlaida as klaida:
        return jsonify({"ok": False, "klaida": str(klaida)})
    return jsonify({"ok": True, "tema": tema, "tekstas": tekstas})


@automatizavimas_bp.route("/sablonai/<int:sablono_id>/salinti", methods=["POST"])
@admin_required
def salinti_sablona(sablono_id):
    sablonas = db.get_or_404(PranesimoSablonas, sablono_id)
    if sablonas.taisykles:
        flash("Šablono pašalinti negalima: jį naudoja taisyklės.", "danger")
        return redirect(url_for("automatizavimas.sablonai"))
    pavadinimas = sablonas.pavadinimas
    db.session.delete(sablonas)
    db.session.commit()
    registruoti("sablonas_pasalintas", "pranesimu_sablonas", sablono_id, pavadinimas)
    flash(f"Šablonas „{pavadinimas}“ pašalintas.", "info")
    return redirect(url_for("automatizavimas.sablonai"))


# --- Siuntimo žurnalas (FR-A09) -----------------------------------------------------

@automatizavimas_bp.route("/zurnalas")
@admin_required
def zurnalas():
    pasirinkti = {
        "busena": request.args.get("busena", ""),
        "kanalas": request.args.get("kanalas", ""),
        "paieska": request.args.get("paieska", "").strip(),
    }
    uzklausa = EilesIrasas.query.join(User, EilesIrasas.gavejo_id == User.id)
    if pasirinkti["busena"] in EilesIrasas.BUSENOS:
        uzklausa = uzklausa.filter(EilesIrasas.busena == pasirinkti["busena"])
    if pasirinkti["kanalas"] in KANALAI:
        uzklausa = uzklausa.filter(EilesIrasas.kanalas == pasirinkti["kanalas"])
    if pasirinkti["paieska"]:
        sablonas = f"%{pasirinkti['paieska']}%"
        uzklausa = uzklausa.filter(or_(
            User.vardas.ilike(sablonas), User.pavarde.ilike(sablonas),
            User.email.ilike(sablonas), EilesIrasas.tema.ilike(sablonas),
        ))
    irasai = uzklausa.order_by(EilesIrasas.id.desc()).paginate(
        page=request.args.get("puslapis", 1, type=int),
        per_page=ZURNALO_PUSLAPIO_DYDIS,
        error_out=False,
    )
    return render_template(
        "automatizavimas/zurnalas.html",
        irasai=irasai,
        pasirinkti=pasirinkti,
        busenos=EilesIrasas.BUSENOS,
        kanalai=KANALAI,
    )


@automatizavimas_bp.route("/zurnalas/<int:iraso_id>/pakartoti", methods=["POST"])
@admin_required
def pakartoti(iraso_id):
    irasas = db.get_or_404(EilesIrasas, iraso_id)
    if PranesimuEile().pakartoti(irasas):
        registruoti("pranesimas_pakartotas", "pranesimu_eile", irasas.id, irasas.tema)
        flash("Pranešimas grąžintas į eilę ir bus išsiųstas per minutę.", "success")
    else:
        flash("Pakartoti galima tik nepavykusį pranešimą.", "warning")
    return redirect(request.referrer or url_for("automatizavimas.zurnalas"))


# --- Naudotojo pranešimų nustatymai (FR-A07) ----------------------------------------

@automatizavimas_bp.route("/mano-nustatymai", methods=["GET", "POST"])
@login_required
def mano_nustatymai():
    tipai = [t for t in IVYKIU_TIPAI.values() if rodomas_nustatymuose(t, current_user)]
    esami = {n.ivykio_tipas: n for n in
             PranesimuNustatymas.query.filter_by(vartotojo_id=current_user.id)}

    if request.method == "POST":
        for tipas in tipai:
            if tipas.privalomas:
                continue  # privalomų pranešimų išjungti negalima
            irasas = esami.get(tipas.kodas)
            if irasas is None:
                irasas = PranesimuNustatymas(vartotojo_id=current_user.id, ivykio_tipas=tipas.kodas)
                db.session.add(irasas)
            irasas.el_pastas = request.form.get(f"el_pastas_{tipas.kodas}") == "on"
        db.session.commit()
        flash("Pranešimų nustatymai išsaugoti.", "success")
        return redirect(url_for("automatizavimas.mano_nustatymai"))

    eilutes = [{
        "tipas": tipas,
        "el_pastas": tipas.privalomas or tipas.kodas not in esami or esami[tipas.kodas].el_pastas,
    } for tipas in tipai]
    return render_template("automatizavimas/nustatymai.html", eilutes=eilutes)
