"""Globali paieška - ieško mokinių, klasių, diplomų ir skelbimų."""
from flask import Blueprint, render_template, request
from flask_login import login_required
from routes.auth import personalas_required

from models import Mokinys, Klase, Diplomas, Skelbimas

search_bp = Blueprint("search", __name__, url_prefix="/paieska")


@search_bp.route("/")
@personalas_required
def index():
    uzklausa = request.args.get("q", "").strip()

    rezultatai = {
        "mokiniai": [],
        "klases": [],
        "diplomai": [],
        "skelbimai": [],
    }

    if uzklausa and len(uzklausa) >= 2:
        like = f"%{uzklausa}%"

        rezultatai["mokiniai"] = (
            Mokinys.query.filter(
                (Mokinys.vardas.ilike(like))
                | (Mokinys.pavarde.ilike(like))
                | (Mokinys.email.ilike(like))
                | (Mokinys.motinos_vardas.ilike(like))
                | (Mokinys.tevo_vardas.ilike(like))
            )
            .order_by(Mokinys.pavarde)
            .limit(20)
            .all()
        )

        rezultatai["klases"] = (
            Klase.query.filter(Klase.pavadinimas.ilike(like))
            .order_by(Klase.pavadinimas)
            .limit(10)
            .all()
        )

        rezultatai["diplomai"] = (
            Diplomas.query.filter(
                (Diplomas.pavadinimas.ilike(like))
                | (Diplomas.seminaras.ilike(like))
                | (Diplomas.aprasymas.ilike(like))
            )
            .order_by(Diplomas.ikeltas.desc())
            .limit(15)
            .all()
        )

        rezultatai["skelbimai"] = (
            Skelbimas.query.filter(
                (Skelbimas.pavadinimas.ilike(like))
                | (Skelbimas.turinys.ilike(like))
            )
            .order_by(Skelbimas.sukurtas.desc())
            .limit(10)
            .all()
        )

    bendras = sum(len(v) for v in rezultatai.values())

    return render_template(
        "search.html",
        uzklausa=uzklausa,
        rezultatai=rezultatai,
        bendras=bendras,
    )
