"""Duomenų bazės modeliai (lentelės).

Šiame faile – praktikų metu sukurti modeliai (9 lentelės). Baigiamajame darbe
pridėtos 14 naujų lentelių aprašytos atskiruose failuose (žr. failo pabaigą):
models/vgk.py, models/dokumentai.py, models/automatizavimas.py, models/importas.py.
"""
import hashlib
import secrets
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSONB
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# JSON laukams: PostgreSQL naudoja jsonb (kaip ER diagramoje), SQLite testuose – JSON tekstą
JSON_LAUKAS = db.JSON().with_variant(JSONB(), "postgresql")


def utc_dabar():
    """Dabartinis UTC laikas be laiko juostos žymės.

    Duomenų bazėje laikas saugomas UTC (kaip ir esamuose modeliuose su
    datetime.utcnow). Ši funkcija grąžina tą patį, tik nenaudoja Python 3.12
    pasenusia pažymėtos datetime.utcnow().
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


tevu_vaiku_lentele = db.Table(
    "tevu_vaiku_rysys",
    db.Column("tevo_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("vaiko_id", db.Integer, db.ForeignKey("mokiniai.id", ondelete="CASCADE"), primary_key=True),
    db.Column("rysio_tipas", db.String(20), nullable=False, default="tevas"),
    db.Column("sukurtas", db.DateTime, default=datetime.utcnow),
)


class User(UserMixin, db.Model):
    """Vartotojas - mokytojas, administratorius arba tėvas."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    vardas = db.Column(db.String(80), nullable=False)
    pavarde = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    telefonas = db.Column(db.String(30), nullable=True)
    slaptazodzio_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="mokytojas")
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)

    dvfa_paslaptis = db.Column(db.String(64), nullable=True)
    dvfa_ijungtas = db.Column(db.Boolean, default=False, nullable=False)

    api_token_hash = db.Column(db.String(128), nullable=True, index=True)
    api_token_data = db.Column(db.DateTime, nullable=True)

    # BD: pareigos Vaiko gerovės komisijoje. None – ne komisijos narys.
    vgk_pareigos = db.Column(db.String(20), nullable=True)

    ROLIU_PAVADINIMAI = {
        "administratorius": "Administratorius",
        "mokytojas": "Mokytojas",
        "tevas": "Tėvas",
    }
    VGK_PAREIGOS = {
        "narys": "Komisijos narys",
        "pirmininkas": "Komisijos pirmininkas",
        "sekretorius": "Komisijos sekretorius",
    }

    diplomai = db.relationship("Diplomas", backref="vartotojas", lazy=True, cascade="all, delete-orphan")
    vadovaujamos_klases = db.relationship("Klase", backref="vadovas", lazy=True)
    skelbimai = db.relationship("Skelbimas", backref="autorius", lazy=True, cascade="all, delete-orphan")

    vaikai = db.relationship(
        "Mokinys",
        secondary=tevu_vaiku_lentele,
        backref=db.backref("tevai", lazy="dynamic"),
        lazy="dynamic",
    )

    def nustatyti_slaptazodi(self, slaptazodis):
        self.slaptazodzio_hash = generate_password_hash(slaptazodis)

    def patikrinti_slaptazodi(self, slaptazodis):
        return check_password_hash(self.slaptazodzio_hash, slaptazodis)

    def sugeneruoti_api_tokena(self):
        """Sukuria naują API prieigos raktą ir grąžina jo aiškų tekstą.
        DB saugomas tik SHA-256 hash - taip token'as niekada nesaugomas plaintext.
        """
        tekstas = secrets.token_urlsafe(32)
        self.api_token_hash = hashlib.sha256(tekstas.encode()).hexdigest()
        self.api_token_data = datetime.utcnow()
        return tekstas

    def anuliuoti_api_tokena(self):
        self.api_token_hash = None
        self.api_token_data = None

    @staticmethod
    def rasti_pagal_api_tokena(tekstas):
        if not tekstas:
            return None
        h = hashlib.sha256(tekstas.encode()).hexdigest()
        return User.query.filter_by(api_token_hash=h).first()

    @property
    def pilnas_vardas(self):
        if not self.pavarde:
            return self.vardas
        return f"{self.vardas} {self.pavarde}"

    @property
    def yra_administratorius(self):
        return self.role == "administratorius"

    @property
    def yra_tevas(self):
        return self.role == "tevas"

    @property
    def yra_mokytojas(self):
        return self.role == "mokytojas"

    @property
    def inicialai(self):
        if not self.pavarde:
            return self.vardas[:2].upper()
        return f"{self.vardas[0]}{self.pavarde[0]}".upper()

    @property
    def roles_pavadinimas(self):
        """Rolės pavadinimas sąsajai (pvz., „Tėvas“, o ne „tevas“)."""
        return self.ROLIU_PAVADINIMAI.get(self.role, self.role.capitalize())

    @property
    def yra_vgk_narys(self):
        """Ar naudotojas paskirtas VGK nariu (bet kurios pareigos)."""
        return self.vgk_pareigos in self.VGK_PAREIGOS

    @property
    def gali_matyti_vgk(self):
        """VGK duomenis mato tik komisijos nariai ir administratorius (FR-V02, NFR-06)."""
        return self.yra_administratorius or self.yra_vgk_narys

    @property
    def gali_planuoti_vgk_posedzius(self):
        """Posėdžius planuoja ir protokolus tvarko pirmininkas arba sekretorius."""
        return self.vgk_pareigos in ("pirmininkas", "sekretorius")


class Klase(db.Model):
    """Mokyklos klasė (pvz., 5A, 10B)."""
    __tablename__ = "klases"

    id = db.Column(db.Integer, primary_key=True)
    pavadinimas = db.Column(db.String(20), unique=True, nullable=False)
    mokslo_metai = db.Column(db.String(20), nullable=False, default="2025-2026")
    vadovo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)

    mokiniai = db.relationship("Mokinys", backref="klase", lazy=True, cascade="all, delete-orphan")

    @property
    def mokiniu_skaicius(self):
        return len(self.mokiniai)


class Mokinys(db.Model):
    """Mokinys, priskirtas klasei."""
    __tablename__ = "mokiniai"

    id = db.Column(db.Integer, primary_key=True)
    vardas = db.Column(db.String(80), nullable=False)
    pavarde = db.Column(db.String(80), nullable=False)
    gimimo_data = db.Column(db.Date, nullable=True)
    email = db.Column(db.String(120), nullable=True)
    telefonas = db.Column(db.String(30), nullable=True)
    adresas = db.Column(db.String(200), nullable=True)
    pastabos = db.Column(db.Text, nullable=True)
    klases_id = db.Column(db.Integer, db.ForeignKey("klases.id"), nullable=False)
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)

    # Motinos duomenys
    motinos_vardas = db.Column(db.String(160), nullable=True)
    motinos_telefonas = db.Column(db.String(30), nullable=True)
    motinos_email = db.Column(db.String(120), nullable=True)

    # Tėvo duomenys
    tevo_vardas = db.Column(db.String(160), nullable=True)
    tevo_telefonas = db.Column(db.String(30), nullable=True)
    tevo_email = db.Column(db.String(120), nullable=True)

    # Mokyklos autobusas
    mokyklos_autobusas = db.Column(db.Boolean, default=False, nullable=False)

    # Nuotrauka
    nuotraukos_failas = db.Column(db.String(300), nullable=True)

    # BD: buvę laukai geroves_komisija, geroves_komisija_data ir
    # geroves_komisija_pastabos perkelti į lentelę vgk_atvejai (migracija 0003).
    # lazy="selectin" – mokinių sąraše atvejai užkraunami viena papildoma užklausa.
    vgk_atvejai = db.relationship(
        "VgkAtvejis",
        back_populates="mokinys",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="VgkAtvejis.sukurta",
    )

    @property
    def pilnas_vardas(self):
        return f"{self.vardas} {self.pavarde}"

    @property
    def inicialai(self):
        return f"{self.vardas[0]}{self.pavarde[0]}".upper()

    # --- Suderinamumas su esamais puslapiais ------------------------------
    # Šablonai ir maršrutai iki BD naudojo mokinys.geroves_komisija ir kt.
    # Dabar šios reikšmės apskaičiuojamos iš naujausio neužbaigto VGK atvejo.

    @property
    def aktyvus_vgk_atvejis(self):
        """Naujausias neužbaigtas VGK atvejis arba None."""
        aktyvus = [a for a in self.vgk_atvejai if a.yra_aktyvus]
        return aktyvus[-1] if aktyvus else None

    @property
    def geroves_komisija(self):
        return self.aktyvus_vgk_atvejis is not None

    @property
    def geroves_komisija_data(self):
        atvejis = self.aktyvus_vgk_atvejis
        return atvejis.sukurta.date() if atvejis else None

    @property
    def geroves_komisija_pastabos(self):
        atvejis = self.aktyvus_vgk_atvejis
        return atvejis.priezastis if atvejis else None


class Diplomas(db.Model):
    """Diplomas, pažyma ar sertifikatas iš seminaro."""
    __tablename__ = "diplomai"

    id = db.Column(db.Integer, primary_key=True)
    pavadinimas = db.Column(db.String(200), nullable=False)
    aprasymas = db.Column(db.Text, nullable=True)
    seminaras = db.Column(db.String(200), nullable=True)
    isdavimo_data = db.Column(db.Date, nullable=True)
    failo_kelias = db.Column(db.String(300), nullable=False)
    originalus_failo_vardas = db.Column(db.String(300), nullable=False)
    failo_tipas = db.Column(db.String(20), nullable=False)
    vartotojo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ikeltas = db.Column(db.DateTime, default=datetime.utcnow)


class Skelbimas(db.Model):
    """Mokyklos skelbimas / pranešimas darbuotojams (ir opcionaliai tėvams)."""
    __tablename__ = "skelbimai"

    id = db.Column(db.Integer, primary_key=True)
    pavadinimas = db.Column(db.String(200), nullable=False)
    turinys = db.Column(db.Text, nullable=False)
    svarbus = db.Column(db.Boolean, default=False)
    matomas_tevams = db.Column(db.Boolean, default=False, nullable=False)
    kategorija = db.Column(db.String(30), nullable=False, default="bendra")
    vartotojo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)


class Renginys(db.Model):
    """Mokyklos renginys / įvykis - matomas tėvams kalendoriuje."""
    __tablename__ = "renginiai"

    id = db.Column(db.Integer, primary_key=True)
    pavadinimas = db.Column(db.String(200), nullable=False)
    aprasymas = db.Column(db.Text, nullable=True)
    pradzios_data = db.Column(db.Date, nullable=False, index=True)
    pradzios_laikas = db.Column(db.Time, nullable=True)
    pabaigos_data = db.Column(db.Date, nullable=True)
    pabaigos_laikas = db.Column(db.Time, nullable=True)
    vieta = db.Column(db.String(200), nullable=True)
    kategorija = db.Column(db.String(30), nullable=False, default="mokyklos")
    matomas_tevams = db.Column(db.Boolean, default=True, nullable=False)
    vartotojo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)

    autorius = db.relationship("User", backref="renginiai", lazy=True)


class VeiklosZurnalas(db.Model):
    """Vartotojo veiklos žurnalas - kas ką ir kada padarė (GDPR reikalavimas)."""
    __tablename__ = "veiklos_zurnalas"

    id = db.Column(db.Integer, primary_key=True)
    vartotojo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    veiksmas = db.Column(db.String(50), nullable=False, index=True)
    objekto_tipas = db.Column(db.String(50), nullable=True)
    objekto_id = db.Column(db.Integer, nullable=True)
    aprasymas = db.Column(db.String(500), nullable=True)
    ip_adresas = db.Column(db.String(50), nullable=True)
    laikas = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    vartotojas = db.relationship("User", backref="veiklos_irasai", lazy=True)


class Pranesimas(db.Model):
    """Vartotojo pranešimas - kaupiamas pranešimų centre (varpelio ikonoje)."""
    __tablename__ = "pranesimai"

    id = db.Column(db.Integer, primary_key=True)
    vartotojo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    pavadinimas = db.Column(db.String(200), nullable=False)
    tekstas = db.Column(db.Text, nullable=True)
    nuoroda = db.Column(db.String(300), nullable=True)
    ikona = db.Column(db.String(30), nullable=False, default="bell")
    tipas = db.Column(db.String(20), nullable=False, default="info")
    perskaitytas = db.Column(db.Boolean, default=False, nullable=False, index=True)
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    vartotojas = db.relationship("User", backref="pranesimai_gauti", lazy=True)


# --- Baigiamojo darbo modeliai (14 naujų lentelių) ---------------------------
# Importuojami failo pabaigoje, nes jie naudoja aukščiau aprašytą „db“ objektą.
from models.vgk import VgkAtvejis, VgkPosedis, VgkSvarstymas, VgkDalyvis, VgkPriemone  # noqa: E402,F401
from models.dokumentai import Dokumentas, DokumentuSkaitiklis, PazymosPrasymas  # noqa: E402,F401
from models.automatizavimas import (  # noqa: E402,F401
    AutomatizavimoTaisykle,
    EilesIrasas,
    PranesimoSablonas,
    PranesimuNustatymas,
)
from models.importas import ImportoSesija, ImportoEilute  # noqa: E402,F401
