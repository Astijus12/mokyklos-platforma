"""Automatizavimo posistemio modeliai – baigiamojo darbo dalis.

Lentelės: automatizavimo_taisykles, pranesimu_sablonai, pranesimu_eile,
pranesimu_nustatymai (aprašo 11 pav. „Automatizavimo ir importo dalies esybių
ir ryšių diagrama“).

Kelias: įvykis -> taisyklės -> eilės įrašai -> fono procesas juos išsiunčia.
"""
from models import db, utc_dabar, JSON_LAUKAS


# Pranešimų kanalai. Taisyklė gali turėti kelis kanalus (pvz., el. paštas ir
# sistemos pranešimų centras), o kiekvienas eilės įrašas – vieną.
KANALAI = {
    "el_pastas": "El. paštas",
    "sistema": "Sistema",
}


class PranesimoSablonas(db.Model):
    """Pranešimo tema ir tekstas su Jinja2 kintamaisiais, pvz., {{ renginys.pavadinimas }}."""
    __tablename__ = "pranesimu_sablonai"

    id = db.Column(db.Integer, primary_key=True)
    # Trumpas pastovus kodas, pagal kurį šabloną randa programos kodas ir pradiniai duomenys
    kodas = db.Column(db.String(50), nullable=False)
    pavadinimas = db.Column(db.String(200), nullable=False)
    tema = db.Column(db.String(200), nullable=False)
    tekstas = db.Column(db.Text, nullable=False)
    atnaujinta = db.Column(db.DateTime, nullable=False, default=utc_dabar, onupdate=utc_dabar)

    __table_args__ = (
        db.UniqueConstraint("kodas", name="uq_pranesimu_sablonai_kodas"),
    )


class AutomatizavimoTaisykle(db.Model):
    """Taisyklė: kokiam įvykiui įvykus, kam, kokiu kanalu ir kokiu šablonu pranešti."""
    __tablename__ = "automatizavimo_taisykles"

    id = db.Column(db.Integer, primary_key=True)
    pavadinimas = db.Column(db.String(200), nullable=False)
    ivykio_tipas = db.Column(db.String(50), nullable=False, index=True)
    # Papildoma sąlyga JSON formatu, pvz., {"matomas_tevams": true}; NULL – be sąlygos
    salyga = db.Column(JSON_LAUKAS, nullable=True)
    # Gavėjų grupės kodas, pvz., "tevai", "atsakingas", "administratoriai"
    gavejai = db.Column(db.String(50), nullable=False)
    # Kanalų kodai, atskirti kableliu, pvz., "el_pastas" arba "el_pastas,sistema"
    kanalas = db.Column(db.String(50), nullable=False, default="el_pastas")
    # Priminimams: kiek dienų iki įvykio siųsti (0 – iš karto)
    poslinkis_d = db.Column(db.Integer, nullable=False, default=0)
    sablono_id = db.Column(db.Integer, db.ForeignKey("pranesimu_sablonai.id"), nullable=False)
    aktyvi = db.Column(db.Boolean, nullable=False, default=True)

    sablonas = db.relationship("PranesimoSablonas", backref="taisykles")

    @property
    def kanalu_sarasas(self):
        """Kanalų kodų sąrašas, pvz., ["el_pastas", "sistema"]."""
        return [k.strip() for k in (self.kanalas or "").split(",") if k.strip()]


class EilesIrasas(db.Model):
    """Vienas siunčiamas pranešimas vienam gavėjui vienu kanalu (pranešimų eilė).

    unikalus_raktas sudaromas iš objekto, taisyklės ir gavėjo identifikatorių,
    todėl to paties pranešimo antrą kartą įrašyti nepavyks (NFR-01).
    """
    __tablename__ = "pranesimu_eile"

    LAUKIA = "laukia"
    SIUNCIAMAS = "siunciamas"
    ISSIUSTAS = "issiustas"
    NEPAVYKO = "nepavyko"
    ATSAUKTAS = "atsauktas"
    BUSENOS = {
        LAUKIA: "Laukia",
        SIUNCIAMAS: "Siunčiamas",
        ISSIUSTAS: "Išsiųstas",
        NEPAVYKO: "Nepavyko",
        ATSAUKTAS: "Atšauktas",
    }

    id = db.Column(db.Integer, primary_key=True)
    gavejo_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Taisyklė gali būti vėliau ištrinta – siuntimo žurnalas lieka
    taisykles_id = db.Column(
        db.Integer, db.ForeignKey("automatizavimo_taisykles.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    kanalas = db.Column(db.String(20), nullable=False)
    tema = db.Column(db.String(200), nullable=False)
    tekstas = db.Column(db.Text, nullable=False)
    unikalus_raktas = db.Column(db.String(200), nullable=False)
    busena = db.Column(db.String(20), nullable=False, default=LAUKIA)
    bandymai = db.Column(db.Integer, nullable=False, default=0)
    # Laikas, nuo kurio įrašą galima siųsti (priminimams ir pakartotiniams bandymams)
    siusti_po = db.Column(db.DateTime, nullable=False, default=utc_dabar)
    issiusta = db.Column(db.DateTime, nullable=True)
    klaida = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("unikalus_raktas", name="uq_pranesimu_eile_unikalus_raktas"),
        db.CheckConstraint(
            "busena IN ('laukia', 'siunciamas', 'issiustas', 'nepavyko', 'atsauktas')",
            name="ck_pranesimu_eile_busena",
        ),
        # Siuntėjo užklausai: „laukiantys įrašai, kurių siusti_po jau praėjo“
        db.Index("ix_pranesimu_eile_busena_siusti_po", "busena", "siusti_po"),
    )

    gavejas = db.relationship("User", foreign_keys=[gavejo_id])
    taisykle = db.relationship("AutomatizavimoTaisykle", foreign_keys=[taisykles_id])

    @property
    def busenos_pavadinimas(self):
        return self.BUSENOS.get(self.busena, self.busena)

    @property
    def kanalo_pavadinimas(self):
        return KANALAI.get(self.kanalas, self.kanalas)


class PranesimuNustatymas(db.Model):
    """Naudotojo pasirinkimas, ar gauti el. laiškus apie tam tikro tipo įvykius (FR-A07).

    Jei įrašo nėra, laikoma, kad el. laiškai siunčiami (numatytoji reikšmė).
    Sistemos pranešimų centre pranešimai rodomi visada.
    """
    __tablename__ = "pranesimu_nustatymai"

    vartotojo_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    ivykio_tipas = db.Column(db.String(50), primary_key=True)
    el_pastas = db.Column(db.Boolean, nullable=False, default=True)

    vartotojas = db.relationship("User", foreign_keys=[vartotojo_id])
