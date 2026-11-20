"""Taisyklių variklis (aprašo 6 pav. klasė TaisykliuVariklis).

Atsako į tris klausimus: kurios aktyvios taisyklės taikomos įvykiui, ar įvykio
objektas tenkina taisyklės sąlygą ir kas yra pranešimo gavėjai.
"""
from collections import namedtuple

from models import AutomatizavimoTaisykle, User

GavejuGrupe = namedtuple("GavejuGrupe", "pavadinimas funkcija")


def _pagal_role(*roles):
    return User.query.filter(User.role.in_(roles)).order_by(User.id).all()


def _tevai(objektas):
    return _pagal_role("tevas")


def _darbuotojai(objektas):
    return _pagal_role("mokytojas", "administratorius")


def _visi(objektas):
    return User.query.order_by(User.id).all()


def _administratoriai(objektas):
    return _pagal_role("administratorius")


def _vgk_nariai(objektas):
    return User.query.filter(User.vgk_pareigos.isnot(None)).order_by(User.id).all()


def _vgk_pirmininkas(objektas):
    return User.query.filter_by(vgk_pareigos="pirmininkas").order_by(User.id).all()


def _posedzio_dalyviai(objektas):
    # Kviestiniai asmenys be paskyros pranešimų negauna – jie kviečiami atskirai
    return [d.vartotojas for d in getattr(objektas, "dalyviai", []) if d.vartotojas is not None]


def _vienas(objektas, atributas):
    reiksme = getattr(objektas, atributas, None)
    return [reiksme] if reiksme is not None else []


def _atsakingas(objektas):
    return _vienas(objektas, "atsakingas")


def _prasymo_teikejas(objektas):
    return _vienas(objektas, "tevas")


def _iniciatorius(objektas):
    return _vienas(objektas, "vartotojas")


def _mokinio_tevai(objektas):
    mokinys = getattr(objektas, "mokinys", None)
    return list(mokinys.tevai) if mokinys is not None else []


def _naujas_naudotojas(objektas):
    return [objektas] if isinstance(objektas, User) else []


# Gavėjų grupės: kodas saugomas taisyklėje (automatizavimo_taisykles.gavejai)
GAVEJU_GRUPES = {
    "tevai": GavejuGrupe("Tėvai", _tevai),
    "darbuotojai": GavejuGrupe("Darbuotojai", _darbuotojai),
    "visi": GavejuGrupe("Visi naudotojai", _visi),
    "administratoriai": GavejuGrupe("Administratorius", _administratoriai),
    "vgk_nariai": GavejuGrupe("Komisijos nariai", _vgk_nariai),
    "vgk_pirmininkas": GavejuGrupe("Komisijos pirmininkas", _vgk_pirmininkas),
    "posedzio_dalyviai": GavejuGrupe("Nariai, tėvai", _posedzio_dalyviai),
    "atsakingas": GavejuGrupe("Atsakingas asmuo", _atsakingas),
    "prasymo_teikejas": GavejuGrupe("Prašymą pateikęs tėvas", _prasymo_teikejas),
    "mokinio_tevai": GavejuGrupe("Mokinio tėvai", _mokinio_tevai),
    "iniciatorius": GavejuGrupe("Veiksmą atlikęs naudotojas", _iniciatorius),
    "naujas_naudotojas": GavejuGrupe("Naujas naudotojas", _naujas_naudotojas),
}


def patikrinti_salyga(salyga):
    """Grąžina klaidos tekstą arba None. Sąlyga – JSON objektas {laukas: reikšmė arba [reikšmės]}."""
    if salyga is None:
        return None
    if not isinstance(salyga, dict):
        return "Sąlyga turi būti JSON objektas, pvz., {\"matomas_tevams\": true}."
    for laukas, reiksme in salyga.items():
        if not laukas or laukas.startswith("_"):
            return f"Netinkamas lauko pavadinimas: „{laukas}“."
        reiksmes = reiksme if isinstance(reiksme, list) else [reiksme]
        if not all(isinstance(r, (str, int, float, bool)) or r is None for r in reiksmes):
            return f"Lauko „{laukas}“ reikšmė turi būti tekstas, skaičius, true/false arba jų sąrašas."
    return None


class TaisykliuVariklis:
    """Taisyklių paieška, sąlygų tikrinimas ir gavėjų nustatymas."""

    def rasti_taisykles(self, tipas):
        """Aktyvios taisyklės nurodytam įvykio tipui."""
        return (
            AutomatizavimoTaisykle.query
            .filter_by(ivykio_tipas=tipas, aktyvi=True)
            .order_by(AutomatizavimoTaisykle.id)
            .all()
        )

    def tenkina_salyga(self, taisykle, objektas):
        """Ar objekto laukai atitinka taisyklės sąlygą (visi nurodyti laukai turi sutapti)."""
        for laukas, laukiama in (taisykle.salyga or {}).items():
            if laukas.startswith("_"):
                return False
            reiksme = getattr(objektas, laukas, None)
            if isinstance(laukiama, list):
                if reiksme not in laukiama:
                    return False
            elif reiksme != laukiama:
                return False
        return True

    def nustatyti_gavejus(self, taisykle, objektas):
        """Gavėjų sąrašas be pasikartojimų, surikiuotas pagal naudotojo id."""
        grupe = GAVEJU_GRUPES.get(taisykle.gavejai)
        if grupe is None:
            return []
        unikalus = {gavejas.id: gavejas for gavejas in grupe.funkcija(objektas) if gavejas is not None}
        return [unikalus[i] for i in sorted(unikalus)]
