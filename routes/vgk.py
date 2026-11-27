"""Vaiko gerovės komisijos (VGK) puslapiai (FR-V01–FR-V11, NFR-06, NFR-09).

Teisės:
- atvejų ir posėdžių duomenis mato tik komisijos nariai ir administratorius,
  kitiems naudotojams grąžinamas 404 (nesužinoma net tai, kad duomenys yra);
- posėdžius planuoja, dalyvius ir nutarimus įrašo pirmininkas, sekretorius
  arba administratorius;
- skubų posėdį (iki jo mažiau nei 5 darbo dienos) tvirtina tik administratorius;
- kreipimąsi gali pateikti bet kuris darbuotojas – jis mato tik savo kreipimųsi būseną;
- priemonę įvykdyta pažymi atsakingas asmuo.
Kiekviena VGK duomenų peržiūra ir keitimas registruojami veiklos žurnale (FR-V11).
"""
from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import Klase, Mokinys, User, VgkAtvejis, VgkPosedis, VgkPriemone, VgkSvarstymas, db
from routes.audit import registruoti
from routes.auth import personalas_required
from services.vgk import (
    MIN_DARBO_DIENU,
    VgkKlaida,
    atmesti_skubu_posedi,
    atnaujinti_atveji,
    atsaukti_posedi,
    dalyviu_grupes,
    darbo_dienu_iki_posedzio,
    data_is_formos,
    gali_pazymeti_priemone,
    gali_uzbaigti,
    galimi_darbotvarkei,
    irasyti_posedzio_duomenis,
    issaugoti_posedi,
    laikas_is_formos,
    pateikti_kreipimasi,
    patvirtinti_skubu_posedi,
    pazymeti_ivykdyta,
    prideti_priemone,
    uzbaigti_atveji,
    uzbaigti_posedi,
)

vgk_bp = Blueprint("vgk", __name__, url_prefix="/vgk")

ATVEJU_SPALVOS = {
    VgkAtvejis.UZREGISTRUOTAS: "tag-blue",
    VgkAtvejis.SVARSTOMAS: "tag-warning",
    VgkAtvejis.TAIKOMOS_PRIEMONES: "tag-purple",
    VgkAtvejis.UZBAIGTAS: "tag-green",
}
PRIEMONIU_SPALVOS = {VgkPriemone.PASKIRTA: "tag-blue", VgkPriemone.VELUOJA: "tag-danger",
                     VgkPriemone.IVYKDYTA: "tag-green"}
POSEDZIU_SPALVOS = {VgkPosedis.JUODRASTIS: "tag-default", VgkPosedis.LAUKIA_PATVIRTINIMO: "tag-blue",
                    VgkPosedis.SUPLANUOTAS: "tag-warning", VgkPosedis.IVYKES: "tag-green",
                    VgkPosedis.ATSAUKTAS: "tag-danger"}


@vgk_bp.context_processor
def spalvos():
    return {"atveju_spalvos": ATVEJU_SPALVOS, "priemoniu_spalvos": PRIEMONIU_SPALVOS,
            "posedziu_spalvos": POSEDZIU_SPALVOS}


def vgk_narys_required(f):
    """Tik komisijos nariams ir administratoriui; kitiems – 404 (NFR-06)."""
    @wraps(f)
    @login_required
    def apgaubta(*args, **kwargs):
        if not current_user.gali_matyti_vgk:
            abort(404)
        return f(*args, **kwargs)
    return apgaubta


def vgk_valdytojas_required(f):
    """Posėdžių planavimas ir nutarimai: pirmininkas, sekretorius ar administratorius."""
    @wraps(f)
    @login_required
    def apgaubta(*args, **kwargs):
        if not current_user.gali_matyti_vgk:
            abort(404)
        if not (current_user.yra_administratorius or current_user.gali_planuoti_vgk_posedzius):
            abort(403)
        return f(*args, **kwargs)
    return apgaubta


def _galima_valdyti():
    return current_user.yra_administratorius or current_user.gali_planuoti_vgk_posedzius


def _darbuotojai():
    return (User.query.filter(User.role.in_(["mokytojas", "administratorius"]))
            .order_by(User.pavarde, User.vardas).all())


# --- Kreipimasis ir mano puslapiai (visiems darbuotojams) --------------------------

@vgk_bp.route("/kreipimasis", methods=["GET", "POST"])
@personalas_required
def kreipimasis():
    """FR-V01: kreipimasis dėl mokinio."""
    if request.method == "POST":
        mokinys = db.session.get(Mokinys, request.form.get("mokinio_id", type=int) or 0)
        try:
            atvejis = pateikti_kreipimasi(current_user, mokinys, request.form.get("priezastis"))
        except VgkKlaida as klaida:
            db.session.rollback()
            flash(str(klaida), "danger")
        else:
            registruoti("vgk_kreipimasis", "vgk_atvejis", atvejis.id, f"Pateiktas kreipimasis nr. {atvejis.numeris}")
            flash(f"Kreipimasis nr. {atvejis.numeris} užregistruotas, komisijos pirmininkui pranešta.", "success")
            return redirect(url_for("vgk.mano_kreipimaisi"))
    klases = Klase.query.order_by(Klase.pavadinimas).all()
    return render_template("vgk/kreipimasis.html", klases=klases,
                           pasirinktas=request.args.get("mokinio_id", type=int))


@vgk_bp.route("/mano-kreipimaisi")
@personalas_required
def mano_kreipimaisi():
    """FR-V02: kreipimąsi pateikęs darbuotojas mato tik savo kreipimųsi būseną."""
    atvejai = (VgkAtvejis.query.filter_by(pateike_id=current_user.id)
               .order_by(VgkAtvejis.sukurta.desc()).all())
    return render_template("vgk/mano_kreipimaisi.html", atvejai=atvejai)


@vgk_bp.route("/mano-priemones")
@personalas_required
def mano_priemones():
    """FR-V08: atsakingam asmeniui paskirtos priemonės."""
    priemones = (VgkPriemone.query.filter_by(atsakingo_id=current_user.id)
                 .order_by((VgkPriemone.busena == VgkPriemone.IVYKDYTA), VgkPriemone.terminas).all())
    return render_template("vgk/mano_priemones.html", priemones=priemones, siandien=date.today())


@vgk_bp.route("/priemones/<int:priemones_id>/ivykdyta", methods=["POST"])
@personalas_required
def priemone_ivykdyta(priemones_id):
    priemone = db.get_or_404(VgkPriemone, priemones_id)
    if not gali_pazymeti_priemone(current_user, priemone):
        abort(404)
    try:
        pazymeti_ivykdyta(priemone, current_user, request.form.get("rezultatas"))
    except VgkKlaida as klaida:
        flash(str(klaida), "warning")
    else:
        registruoti("vgk_priemone_ivykdyta", "vgk_priemone", priemone.id, "Priemonė pažymėta įvykdyta")
        flash("Priemonė pažymėta įvykdyta.", "success")
    return redirect(request.referrer or url_for("vgk.mano_priemones"))


# --- Atvejai (komisijos nariams) ------------------------------------------------------

@vgk_bp.route("/")
@vgk_narys_required
def atvejai():
    busena = request.args.get("busena", "")
    uzklausa = VgkAtvejis.query
    if busena in VgkAtvejis.BUSENOS:
        uzklausa = uzklausa.filter_by(busena=busena)
    sarasas = uzklausa.order_by(VgkAtvejis.sukurta.desc()).all()
    registruoti("vgk_perziura", "vgk_atvejai", None, "Peržiūrėtas atvejų sąrašas")
    return render_template("vgk/atvejai.html", atvejai=sarasas, busena=busena, busenos=VgkAtvejis.BUSENOS,
                           galima_valdyti=_galima_valdyti())


@vgk_bp.route("/atvejai/<int:atvejo_id>")
@vgk_narys_required
def atvejis(atvejo_id):
    """Atvejo kortelė (aprašo 12 pav. maketas)."""
    a = db.get_or_404(VgkAtvejis, atvejo_id)
    registruoti("vgk_perziura", "vgk_atvejis", a.id, f"Peržiūrėtas atvejis nr. {a.numeris}")
    paskutinis = next((s for s in reversed(a.svarstymai)
                       if s.posedis.busena in (VgkPosedis.SUPLANUOTAS, VgkPosedis.IVYKES)), None)
    return render_template("vgk/atvejis.html", atvejis=a, paskutinis_svarstymas=paskutinis,
                           galima_valdyti=_galima_valdyti(), gali_uzbaigti=gali_uzbaigti(a),
                           darbuotojai=_darbuotojai(), siandien=date.today())


@vgk_bp.route("/atvejai/<int:atvejo_id>/priemones", methods=["POST"])
@vgk_valdytojas_required
def atvejo_priemone(atvejo_id):
    """„Pridėti priemonę“ atvejo kortelėje: priemonė priskiriama paskutiniam svarstymui."""
    svarstymas = db.get_or_404(VgkSvarstymas, request.form.get("svarstymo_id", type=int) or 0)
    if svarstymas.atvejo_id != atvejo_id:
        abort(404)
    _prideti_priemone(svarstymas)
    return redirect(url_for("vgk.atvejis", atvejo_id=atvejo_id))


def _prideti_priemone(svarstymas):
    atsakingas = db.session.get(User, request.form.get("atsakingo_id", type=int) or 0)
    try:
        priemone = prideti_priemone(svarstymas, request.form.get("aprasymas"), atsakingas,
                                    data_is_formos(request.form.get("terminas")))
    except VgkKlaida as klaida:
        db.session.rollback()
        flash(str(klaida), "danger")
    else:
        registruoti("vgk_priemone_paskirta", "vgk_priemone", priemone.id,
                    f"Paskirta priemonė atvejui nr. {svarstymas.atvejis.numeris}")
        flash("Priemonė paskirta.", "success")


@vgk_bp.route("/atvejai/<int:atvejo_id>/uzbaigti", methods=["POST"])
@vgk_narys_required
def uzbaigti(atvejo_id):
    a = db.get_or_404(VgkAtvejis, atvejo_id)
    try:
        uzbaigti_atveji(a)
    except VgkKlaida as klaida:
        flash(str(klaida), "warning")
    else:
        registruoti("vgk_atvejis_uzbaigtas", "vgk_atvejis", a.id, f"Užbaigtas atvejis nr. {a.numeris}")
        flash(f"Atvejis nr. {a.numeris} užbaigtas.", "success")
    return redirect(url_for("vgk.atvejis", atvejo_id=a.id))


@vgk_bp.route("/atvejai/<int:atvejo_id>/atnaujinti", methods=["POST"])
@vgk_narys_required
def atnaujinti(atvejo_id):
    a = db.get_or_404(VgkAtvejis, atvejo_id)
    try:
        atnaujinti_atveji(a)
    except VgkKlaida as klaida:
        flash(str(klaida), "warning")
    else:
        registruoti("vgk_atvejis_atnaujintas", "vgk_atvejis", a.id, f"Atnaujintas atvejis nr. {a.numeris}")
        flash(f"Atvejis nr. {a.numeris} atnaujintas ir laukia svarstymo.", "success")
    return redirect(url_for("vgk.atvejis", atvejo_id=a.id))


# --- Posėdžiai -------------------------------------------------------------------------

@vgk_bp.route("/posedziai")
@vgk_narys_required
def posedziai():
    sarasas = VgkPosedis.query.order_by(VgkPosedis.data.desc(), VgkPosedis.laikas.desc()).all()
    return render_template("vgk/posedziai.html", posedziai=sarasas, galima_valdyti=_galima_valdyti())


@vgk_bp.route("/darbo-dienos")
@vgk_valdytojas_required
def darbo_dienos():
    """Formai: kiek darbo dienų liko iki pasirinktos datos (FR-V04)."""
    data = data_is_formos(request.args.get("data"))
    if data is None:
        return jsonify({"klaida": "Netinkama data"}), 400
    liko = darbo_dienu_iki_posedzio(data)
    return jsonify({"liko": liko, "pakanka": liko >= MIN_DARBO_DIENU, "reikia": MIN_DARBO_DIENU})


@vgk_bp.route("/posedziai/naujas", methods=["GET", "POST"])
@vgk_bp.route("/posedziai/<int:posedzio_id>/redaguoti", methods=["GET", "POST"])
@vgk_valdytojas_required
def posedzio_forma(posedzio_id=None):
    """Posėdžio planavimas (aprašo 13 pav. maketas, 2 lentelės panaudos atvejis)."""
    posedis = db.get_or_404(VgkPosedis, posedzio_id) if posedzio_id else None
    if posedis is not None and posedis.busena != VgkPosedis.JUODRASTIS:
        flash("Redaguoti galima tik posėdžio juodraštį.", "warning")
        return redirect(url_for("vgk.posedis", posedzio_id=posedis.id))
    kandidatai = galimi_darbotvarkei()

    if request.method == "POST":
        pasirinkti_id = {int(x) for x in request.form.getlist("atvejai") if x.isdigit()}
        atvejai = [a for a in kandidatai if a.id in pasirinkti_id]
        patvirtinti = request.form.get("veiksmas") == "patvirtinti"
        try:
            posedis = issaugoti_posedi(
                posedis,
                data_is_formos(request.form.get("data")),
                laikas_is_formos(request.form.get("laikas")),
                request.form.get("vieta"),
                atvejai,
                set(request.form.getlist("grupes")),
                kviestiniai=request.form.get("kviestiniai", ""),
                skubos_priezastis=request.form.get("skubos_priezastis", ""),
                patvirtinti=patvirtinti,
                administratorius=current_user.yra_administratorius,
            )
        except VgkKlaida as klaida:
            db.session.rollback()
            flash(str(klaida), "danger")
            posedis = db.session.get(VgkPosedis, posedzio_id) if posedzio_id else None
        else:
            if patvirtinti and posedis.busena == VgkPosedis.LAUKIA_PATVIRTINIMO:
                registruoti("vgk_posedis_pateiktas_tvirtinti", "vgk_posedis", posedis.id,
                            f"Skubus posėdis {posedis.data:%Y-%m-%d} perduotas administratoriui patvirtinti")
                flash("Iki posėdžio liko mažiau nei 5 darbo dienos, todėl jis perduotas administratoriui "
                      "patvirtinti. Kvietimai bus išsiųsti tik po patvirtinimo.", "info")
                return redirect(url_for("vgk.posedis", posedzio_id=posedis.id))
            if patvirtinti:
                registruoti("vgk_posedis_suplanuotas", "vgk_posedis", posedis.id,
                            f"Suplanuotas posėdis {posedis.data:%Y-%m-%d}, išsiųsti kvietimai")
                flash("Posėdis suplanuotas, kvietimai išsiųsti dalyviams.", "success")
                return redirect(url_for("vgk.posedis", posedzio_id=posedis.id))
            registruoti("vgk_posedis_juodrastis", "vgk_posedis", posedis.id, "Išsaugotas posėdžio juodraštis")
            flash("Posėdžio juodraštis išsaugotas. Kvietimai dar neišsiųsti.", "info")
            return redirect(url_for("vgk.posedzio_forma", posedzio_id=posedis.id))

    # Pažymėti atvejai: iš juodraščio, iš nuorodos „Įtraukti į posėdį“ arba iš ką tik pateiktos formos
    if request.method == "POST":
        pazymeti = {int(x) for x in request.form.getlist("atvejai") if x.isdigit()}
    elif posedis is not None:
        pazymeti = {s.atvejo_id for s in posedis.svarstymai}
    else:
        pazymeti = {int(x) for x in request.args.getlist("atvejai") if x.isdigit()}

    grupes = dalyviu_grupes(kandidatai)
    if posedis is not None:
        dalyviu_id = {d.vartotojo_id for d in posedis.dalyviai if d.vartotojo_id}
        pazymetos_grupes = {kodas for kodas, _, nariai in grupes if any(n.id in dalyviu_id for n, _ in nariai)}
        kviestiniai = "\n".join(d.vardas_pavarde for d in posedis.dalyviai if d.vartotojo_id is None)
    else:
        pazymetos_grupes = {kodas for kodas, _, _ in grupes}
        kviestiniai = ""
    return render_template("vgk/posedzio_forma.html", posedis=posedis, kandidatai=kandidatai,
                           pazymeti=pazymeti, grupes=grupes, pazymetos_grupes=pazymetos_grupes,
                           kviestiniai=kviestiniai, forma=request.form if request.method == "POST" else None,
                           reikia_dienu=MIN_DARBO_DIENU)


@vgk_bp.route("/posedziai/<int:posedzio_id>")
@vgk_narys_required
def posedis(posedzio_id):
    p = db.get_or_404(VgkPosedis, posedzio_id)
    registruoti("vgk_perziura", "vgk_posedis", p.id, f"Peržiūrėtas posėdis {p.data:%Y-%m-%d}")
    return render_template("vgk/posedis.html", posedis=p, galima_valdyti=_galima_valdyti(),
                           darbuotojai=_darbuotojai(), siandien=date.today())


@vgk_bp.route("/posedziai/<int:posedzio_id>/duomenys", methods=["POST"])
@vgk_valdytojas_required
def posedzio_duomenys(posedzio_id):
    """FR-V06: dalyvavimas, konfidencialumo pasižadėjimai ir nutarimai."""
    p = db.get_or_404(VgkPosedis, posedzio_id)
    dalyvavo = {int(x) for x in request.form.getlist("dalyvavo") if x.isdigit()}
    pasizadejimas = {int(x) for x in request.form.getlist("pasizadejimas") if x.isdigit()}
    nutarimai = {s.id: request.form.get(f"nutarimas_{s.id}") for s in p.svarstymai
                 if f"nutarimas_{s.id}" in request.form}
    try:
        irasyti_posedzio_duomenis(p, dalyvavo, pasizadejimas, nutarimai)
    except VgkKlaida as klaida:
        flash(str(klaida), "danger")
    else:
        registruoti("vgk_posedzio_duomenys", "vgk_posedis", p.id, "Įrašyti dalyviai ir nutarimai")
        flash("Posėdžio duomenys išsaugoti.", "success")
    return redirect(url_for("vgk.posedis", posedzio_id=p.id))


@vgk_bp.route("/posedziai/<int:posedzio_id>/svarstymai/<int:svarstymo_id>/priemones", methods=["POST"])
@vgk_valdytojas_required
def posedzio_priemone(posedzio_id, svarstymo_id):
    svarstymas = db.get_or_404(VgkSvarstymas, svarstymo_id)
    if svarstymas.posedzio_id != posedzio_id:
        abort(404)
    _prideti_priemone(svarstymas)
    return redirect(url_for("vgk.posedis", posedzio_id=posedzio_id) + f"#svarstymas-{svarstymo_id}")


@vgk_bp.route("/posedziai/<int:posedzio_id>/uzbaigti", methods=["POST"])
@vgk_valdytojas_required
def uzbaigti_posedi_marsrutas(posedzio_id):
    """FR-V07: posėdis įvyko – sugeneruojamas protokolo projektas."""
    p = db.get_or_404(VgkPosedis, posedzio_id)
    try:
        protokolas = uzbaigti_posedi(p, current_user)
    except VgkKlaida as klaida:
        db.session.rollback()
        flash(str(klaida), "danger")
    else:
        registruoti("vgk_protokolas", "dokumentas", protokolas.id, f"Parengtas protokolas {protokolas.numeris}")
        flash(f"Posėdis užbaigtas, parengtas protokolo projektas {protokolas.numeris}.", "success")
    return redirect(url_for("vgk.posedis", posedzio_id=posedzio_id))


@vgk_bp.route("/posedziai/<int:posedzio_id>/atsaukti", methods=["POST"])
@vgk_valdytojas_required
def atsaukti(posedzio_id):
    p = db.get_or_404(VgkPosedis, posedzio_id)
    try:
        atsaukti_posedi(p)
    except VgkKlaida as klaida:
        flash(str(klaida), "warning")
    else:
        registruoti("vgk_posedis_atsauktas", "vgk_posedis", p.id, f"Atšauktas posėdis {p.data:%Y-%m-%d}")
        flash("Posėdis atšauktas, dalyviams pranešta.", "info")
    return redirect(url_for("vgk.posedziai"))


# --- Skubaus posėdžio tvirtinimas (FR-V04): tik administratorius ---------------------

@vgk_bp.route("/posedziai/<int:posedzio_id>/patvirtinti", methods=["POST"])
@vgk_narys_required
def patvirtinti_skubu(posedzio_id):
    if not current_user.yra_administratorius:
        abort(403)
    p = db.get_or_404(VgkPosedis, posedzio_id)
    try:
        patvirtinti_skubu_posedi(p)
    except VgkKlaida as klaida:
        db.session.rollback()
        flash(str(klaida), "danger")
    else:
        registruoti("vgk_posedis_patvirtintas", "vgk_posedis", p.id,
                    f"Administratorius patvirtino skubų posėdį {p.data:%Y-%m-%d}, išsiųsti kvietimai")
        flash("Skubus posėdis patvirtintas, kvietimai išsiųsti dalyviams.", "success")
    return redirect(url_for("vgk.posedis", posedzio_id=posedzio_id))


@vgk_bp.route("/posedziai/<int:posedzio_id>/atmesti", methods=["POST"])
@vgk_narys_required
def atmesti_skubu(posedzio_id):
    if not current_user.yra_administratorius:
        abort(403)
    p = db.get_or_404(VgkPosedis, posedzio_id)
    try:
        atmesti_skubu_posedi(p, request.form.get("atmetimo_priezastis"))
    except VgkKlaida as klaida:
        db.session.rollback()
        flash(str(klaida), "danger")
    else:
        registruoti("vgk_posedis_atmestas", "vgk_posedis", p.id,
                    f"Administratorius atmetė skubų posėdį {p.data:%Y-%m-%d}")
        flash("Skubus posėdis atmestas ir grąžintas į juodraščius, pirmininkui ir sekretoriui pranešta.", "info")
    return redirect(url_for("vgk.posedis", posedzio_id=posedzio_id))
