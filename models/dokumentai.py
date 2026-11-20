"""Dokumentų modeliai – baigiamojo darbo dalis.

Lentelės: dokumentai, dokumentu_skaitikliai, pazymu_prasymai
(aprašo 10 pav. „VGK ir dokumentų dalies esybių ir ryšių diagrama“).
"""
from models import db, utc_dabar


class Dokumentas(db.Model):
    """Sugeneruoto PDF dokumento įrašas dokumentų registre (FR-D04, FR-D05, NFR-11)."""
    __tablename__ = "dokumentai"

    # Dokumento tipo kodas naudojamas ir numerio pradžioje, pvz., PZ-2026-0042
    TIPAI = {
        "PZ": "Pažyma",
        "PR": "VGK posėdžio protokolas",
        "AT": "Ataskaita",
    }

    id = db.Column(db.Integer, primary_key=True)
    numeris = db.Column(db.String(30), nullable=False)
    tipas = db.Column(db.String(10), nullable=False, index=True)
    # Protokolai ir suvestinės nesusiję su vienu mokiniu, todėl laukas neprivalomas
    mokinio_id = db.Column(
        db.Integer, db.ForeignKey("mokiniai.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sukure_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    failo_kelias = db.Column(db.String(300), nullable=False)
    # SHA-256 kontrolinė suma šešioliktainiu pavidalu (64 simboliai)
    sha256 = db.Column(db.String(64), nullable=False)
    sukurta = db.Column(db.DateTime, nullable=False, default=utc_dabar, index=True)

    __table_args__ = (
        db.UniqueConstraint("numeris", name="uq_dokumentai_numeris"),
    )

    mokinys = db.relationship("Mokinys", foreign_keys=[mokinio_id])
    sukure = db.relationship("User", foreign_keys=[sukure_id])

    @property
    def tipo_pavadinimas(self):
        return self.TIPAI.get(self.tipas, self.tipas)


class DokumentuSkaitiklis(db.Model):
    """Paskutinis panaudotas numeris pagal dokumento tipą ir metus.

    Pirminis raktas sudėtinis (tipas, metai). Numeris didinamas užrakinus
    eilutę (SELECT ... FOR UPDATE), todėl du dokumentai negauna to paties numerio.
    """
    __tablename__ = "dokumentu_skaitikliai"

    tipas = db.Column(db.String(10), primary_key=True)
    metai = db.Column(db.Integer, primary_key=True)
    paskutinis_nr = db.Column(db.Integer, nullable=False, default=0)


class PazymosPrasymas(db.Model):
    """Tėvo prašymas parengti pažymą apie vaiką (FR-D01–FR-D03)."""
    __tablename__ = "pazymu_prasymai"

    PATEIKTAS = "pateiktas"
    IVYKDYTAS = "ivykdytas"
    ATMESTAS = "atmestas"
    BUSENOS = {
        PATEIKTAS: "Pateiktas",
        IVYKDYTAS: "Įvykdytas",
        ATMESTAS: "Atmestas",
    }

    id = db.Column(db.Integer, primary_key=True)
    tevo_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mokinio_id = db.Column(
        db.Integer, db.ForeignKey("mokiniai.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paskirtis = db.Column(db.String(200), nullable=False)
    busena = db.Column(db.String(20), nullable=False, default=PATEIKTAS, index=True)
    nagrinejo_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    dokumento_id = db.Column(
        db.Integer, db.ForeignKey("dokumentai.id", ondelete="SET NULL"), nullable=True
    )
    pateikta = db.Column(db.DateTime, nullable=False, default=utc_dabar)
    # FR-D02: atmetant prašymą nurodoma priežastis
    atmetimo_priezastis = db.Column(db.Text, nullable=True)

    tevas = db.relationship("User", foreign_keys=[tevo_id])
    mokinys = db.relationship("Mokinys", foreign_keys=[mokinio_id])
    nagrinejo = db.relationship("User", foreign_keys=[nagrinejo_id])
    dokumentas = db.relationship("Dokumentas", foreign_keys=[dokumento_id])

    @property
    def busenos_pavadinimas(self):
        return self.BUSENOS.get(self.busena, self.busena)
