"""Duomenų bazės modeliai (lentelės)."""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Vartotojas - mokytojas arba administratorius."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    vardas = db.Column(db.String(80), nullable=False)
    pavarde = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    slaptazodzio_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="mokytojas")
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)

    diplomai = db.relationship("Diplomas", backref="vartotojas", lazy=True, cascade="all, delete-orphan")
    vadovaujamos_klases = db.relationship("Klase", backref="vadovas", lazy=True)
    skelbimai = db.relationship("Skelbimas", backref="autorius", lazy=True, cascade="all, delete-orphan")
    rasyti_pazymiai = db.relationship("Pazymys", backref="mokytojas", lazy=True)

    def nustatyti_slaptazodi(self, slaptazodis):
        self.slaptazodzio_hash = generate_password_hash(slaptazodis)

    def patikrinti_slaptazodi(self, slaptazodis):
        return check_password_hash(self.slaptazodzio_hash, slaptazodis)

    @property
    def pilnas_vardas(self):
        return f"{self.vardas} {self.pavarde}"

    @property
    def yra_administratorius(self):
        return self.role == "administratorius"

    @property
    def inicialai(self):
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

    pazymiai = db.relationship("Pazymys", backref="mokinys", lazy=True, cascade="all, delete-orphan")

    @property
    def pilnas_vardas(self):
        return f"{self.vardas} {self.pavarde}"

    @property
    def inicialai(self):
        return f"{self.vardas[0]}{self.pavarde[0]}".upper()

    @property
    def vidurkis(self):
        """Bendras visų pažymių vidurkis."""
        if not self.pazymiai:
            return None
        return round(sum(p.pazymys for p in self.pazymiai) / len(self.pazymiai), 2)

    def vidurkis_dalyko(self, dalykas):
        """Pažymių vidurkis konkretaus dalyko."""
        pazymiai = [p.pazymys for p in self.pazymiai if p.dalykas == dalykas]
        if not pazymiai:
            return None
        return round(sum(pazymiai) / len(pazymiai), 2)


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
    """Mokyklos skelbimas / pranešimas darbuotojams."""
    __tablename__ = "skelbimai"

    id = db.Column(db.Integer, primary_key=True)
    pavadinimas = db.Column(db.String(200), nullable=False)
    turinys = db.Column(db.Text, nullable=False)
    svarbus = db.Column(db.Boolean, default=False)
    vartotojo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)


class Pazymys(db.Model):
    """Mokinio pažymys iš konkretaus dalyko."""
    __tablename__ = "pazymiai"

    id = db.Column(db.Integer, primary_key=True)
    mokinio_id = db.Column(db.Integer, db.ForeignKey("mokiniai.id"), nullable=False)
    mokytojo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    dalykas = db.Column(db.String(80), nullable=False)
    pazymys = db.Column(db.Integer, nullable=False)
    komentaras = db.Column(db.String(300), nullable=True)
    data = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)


# Galimi dalykai (statinis sąrašas, kad būtų paprasčiau)
DALYKAI = [
    "Matematika",
    "Lietuvių kalba",
    "Anglų kalba",
    "Istorija",
    "Geografija",
    "Biologija",
    "Chemija",
    "Fizika",
    "Informatika",
    "Kūno kultūra",
    "Dailė",
    "Muzika",
    "Technologijos",
    "Etika",
]
