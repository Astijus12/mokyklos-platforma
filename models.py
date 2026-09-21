"""Duomenų bazės modeliai (lentelės)."""
import hashlib
import secrets
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


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

    # Gerovės komisija
    geroves_komisija = db.Column(db.Boolean, default=False, nullable=False)
    geroves_komisija_data = db.Column(db.Date, nullable=True)
    geroves_komisija_pastabos = db.Column(db.Text, nullable=True)

    @property
    def pilnas_vardas(self):
        return f"{self.vardas} {self.pavarde}"

    @property
    def inicialai(self):
        return f"{self.vardas[0]}{self.pavarde[0]}".upper()


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
    vartotojo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)
