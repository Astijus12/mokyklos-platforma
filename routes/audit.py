"""Veiklos žurnalo peržiūra (tik administratoriams)."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request
from flask_login import current_user

from models import db, VeiklosZurnalas, User
from routes.auth import admin_required

audit_bp = Blueprint("audit", __name__, url_prefix="/veikla")


def registruoti(veiksmas, objekto_tipas=None, objekto_id=None, aprasymas=None):
    """Įrašo veiksmą į veiklos žurnalą."""
    try:
        ip = None
        if request:
            ip = request.remote_addr

        vartotojo_id = current_user.id if current_user and current_user.is_authenticated else None

        irasas = VeiklosZurnalas(
            vartotojo_id=vartotojo_id,
            veiksmas=veiksmas,
            objekto_tipas=objekto_tipas,
            objekto_id=objekto_id,
            aprasymas=aprasymas[:500] if aprasymas else None,
            ip_adresas=ip,
        )
        db.session.add(irasas)
        db.session.commit()
    except Exception:
        db.session.rollback()


@audit_bp.route("/")
@admin_required
def zurnalas():
    """Rodo veiklos žurnalą su filtrais."""
    puslapis = request.args.get("puslapis", 1, type=int)
    vartotojo_id = request.args.get("vartotojo_id", type=int)
    veiksmas = request.args.get("veiksmas", "").strip()
    dienu = request.args.get("dienu", 30, type=int)

    q = VeiklosZurnalas.query

    if vartotojo_id:
        q = q.filter_by(vartotojo_id=vartotojo_id)
    if veiksmas:
        q = q.filter_by(veiksmas=veiksmas)
    if dienu > 0:
        pradzia = datetime.utcnow() - timedelta(days=dienu)
        q = q.filter(VeiklosZurnalas.laikas >= pradzia)

    irasai = q.order_by(VeiklosZurnalas.laikas.desc()).paginate(
        page=puslapis, per_page=50, error_out=False
    )

    vartotojai = User.query.order_by(User.pavarde, User.vardas).all()

    veiksmu_tipai = db.session.query(VeiklosZurnalas.veiksmas).distinct().all()
    veiksmu_tipai = sorted([v[0] for v in veiksmu_tipai])

    return render_template(
        "audit/zurnalas.html",
        irasai=irasai,
        vartotojai=vartotojai,
        veiksmu_tipai=veiksmu_tipai,
        pasirinkti={
            "vartotojo_id": vartotojo_id,
            "veiksmas": veiksmas,
            "dienu": dienu,
        },
    )
