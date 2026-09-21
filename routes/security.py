"""Saugumo funkcijos: dviejų veiksnių autentikacija (2FA / TOTP)."""
import base64
import io

import pyotp
import qrcode
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
)
from flask_login import login_required, current_user, login_user

from models import db, User

security_bp = Blueprint("security", __name__, url_prefix="/saugumas")

SISTEMOS_PAVADINIMAS = "Noriūnų J. Černiaus mokykla"


def _generuoti_qr_data_uri(otp_uri):
    """Sugeneruoja QR kodo Data URI iš otpauth URI."""
    img = qrcode.make(otp_uri)
    buferis = io.BytesIO()
    img.save(buferis, format="PNG")
    kodas = base64.b64encode(buferis.getvalue()).decode("ascii")
    return f"data:image/png;base64,{kodas}"


@security_bp.route("/2fa")
@login_required
def busena():
    """Rodo 2FA būseną (įjungta / išjungta)."""
    return render_template("security/busena.html")


@security_bp.route("/api-tokenas", methods=["GET", "POST"])
@login_required
def api_tokenas():
    """API tokeno valdymas - sukūrimas, peržiūra, anuliavimas."""
    naujas_tokenas = None
    veiksmas = request.form.get("veiksmas")

    if request.method == "POST" and veiksmas == "generuoti":
        naujas_tokenas = current_user.sugeneruoti_api_tokena()
        db.session.commit()
        flash(
            "Sugeneruotas naujas API tokenas. Nukopijuokite jį dabar — antrą kartą jo pamatyti negalėsite.",
            "success",
        )

    elif request.method == "POST" and veiksmas == "anuliuoti":
        current_user.anuliuoti_api_tokena()
        db.session.commit()
        flash("API tokenas anuliuotas.", "info")
        return redirect(url_for("security.api_tokenas"))

    return render_template("security/api_tokenas.html", naujas_tokenas=naujas_tokenas)


@security_bp.route("/2fa/ijungti", methods=["GET", "POST"])
@login_required
def ijungti():
    """Įjungti 2FA - QR kodo generavimas ir kodo patvirtinimas."""
    if current_user.dvfa_ijungtas:
        flash("Dviejų veiksnių autentikacija jau įjungta.", "info")
        return redirect(url_for("security.busena"))

    if request.method == "POST":
        paslaptis = session.get("nauja_dvfa_paslaptis")
        kodas = request.form.get("kodas", "").strip().replace(" ", "")

        if not paslaptis:
            flash("Sesija pasibaigė. Bandykite iš naujo.", "danger")
            return redirect(url_for("security.ijungti"))

        totp = pyotp.TOTP(paslaptis)
        if totp.verify(kodas, valid_window=1):
            current_user.dvfa_paslaptis = paslaptis
            current_user.dvfa_ijungtas = True
            db.session.commit()
            session.pop("nauja_dvfa_paslaptis", None)
            flash("Dviejų veiksnių autentikacija sėkmingai įjungta!", "success")
            return redirect(url_for("security.busena"))

        flash("Neteisingas kodas. Patikrinkite savo autentikatoriaus programėlę.", "danger")

    paslaptis = pyotp.random_base32()
    session["nauja_dvfa_paslaptis"] = paslaptis

    otp_uri = pyotp.TOTP(paslaptis).provisioning_uri(
        name=current_user.email,
        issuer_name=SISTEMOS_PAVADINIMAS,
    )
    qr_data_uri = _generuoti_qr_data_uri(otp_uri)

    return render_template(
        "security/ijungti.html",
        paslaptis=paslaptis,
        qr_data_uri=qr_data_uri,
    )


@security_bp.route("/2fa/isjungti", methods=["POST"])
@login_required
def isjungti():
    """Išjungti 2FA - reikia patvirtinti slaptažodžiu."""
    slaptazodis = request.form.get("slaptazodis", "")

    if not current_user.patikrinti_slaptazodi(slaptazodis):
        flash("Neteisingas slaptažodis.", "danger")
        return redirect(url_for("security.busena"))

    current_user.dvfa_ijungtas = False
    current_user.dvfa_paslaptis = None
    db.session.commit()
    flash("Dviejų veiksnių autentikacija išjungta.", "info")
    return redirect(url_for("security.busena"))


@security_bp.route("/2fa/patvirtinti", methods=["GET", "POST"])
def patvirtinti():
    """Antras prisijungimo žingsnis - įvesti TOTP kodą po slaptažodžio."""
    vartotojo_id = session.get("dvfa_lauke_vartotojo_id")
    if not vartotojo_id:
        return redirect(url_for("auth.login"))

    vartotojas = db.session.get(User, vartotojo_id)
    if not vartotojas or not vartotojas.dvfa_ijungtas:
        session.pop("dvfa_lauke_vartotojo_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        kodas = request.form.get("kodas", "").strip().replace(" ", "")
        totp = pyotp.TOTP(vartotojas.dvfa_paslaptis)

        if totp.verify(kodas, valid_window=1):
            session.pop("dvfa_lauke_vartotojo_id", None)
            login_user(vartotojas, remember=True)
            flash(f"Sveiki sugrįžę, {vartotojas.vardas}!", "success")
            if vartotojas.yra_tevas:
                return redirect(url_for("parents.dashboard"))
            return redirect(url_for("dashboard.index"))

        flash("Neteisingas 2FA kodas. Bandykite dar kartą.", "danger")

    return render_template("security/patvirtinti.html", vartotojas=vartotojas)
