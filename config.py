"""Konfigūracijos failas - čia laikomi visi nustatymai."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Kūrimo aplinkoje nustatymai (pvz., DATABASE_URL vietiniam PostgreSQL) laikomi
# faile .env (jis neįtraukiamas į git). Jau nustatyti aplinkos kintamieji
# (Docker, Render) neperrašomi.
load_dotenv(os.path.join(BASE_DIR, ".env"))


def sistemos_adresas(aplinka=None):
    """Adresas nuorodoms el. laiškuose: SISTEMOS_ADRESAS, o Render'yje – jo pateikiamas
    RENDER_EXTERNAL_URL (pvz., https://mokyklos-platforma-1.onrender.com)."""
    aplinka = os.environ if aplinka is None else aplinka
    return aplinka.get("SISTEMOS_ADRESAS") or aplinka.get("RENDER_EXTERNAL_URL") or "http://127.0.0.1:5000"


def normalizuoti_db_adresa(adresas):
    """PostgreSQL adresui aiškiai nurodo tvarkyklę psycopg2 (ji įdiegta – psycopg2-binary).

    Render ir Heroku pateikia „postgres://...“, o naujesnės SQLAlchemy versijos be
    nurodytos tvarkyklės renkasi psycopg (3), kurios projekte nėra.
    """
    if adresas and adresas.startswith(("postgres://", "postgresql://")):
        return "postgresql+psycopg2://" + adresas.split("://", 1)[1]
    return adresas


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "demo-slaptas-raktas-pakeisk-pries-naudojant")

    DATABASE_URL = normalizuoti_db_adresa(os.environ.get("DATABASE_URL"))

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{os.path.join(BASE_DIR, 'mokykla.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

    # --- Automatizavimas: pranešimai ir el. paštas (BD) ---
    MOKYKLOS_PAVADINIMAS = "Noriūnų Jono Černiaus mokykla"
    # Kilmininkas dokumentų tekstui: „mokosi ... mokyklos 5A klasėje“
    MOKYKLOS_PAVADINIMAS_KILMININKAS = "Noriūnų Jono Černiaus mokyklos"
    # Adresas nuorodoms el. laiškuose (fono procesas neturi HTTP užklausos, todėl nurodomas čia)
    # (Docker Compose nenurodytą kintamąjį perduoda kaip tuščią eilutę, todėl naudojamas „or“)
    SISTEMOS_ADRESAS = sistemos_adresas()
    MAIL_SERVER = os.environ.get("MAIL_SERVER") or None
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = (os.environ.get("MAIL_USE_TLS") or "true").lower() == "true"
    MAIL_USE_SSL = (os.environ.get("MAIL_USE_SSL") or "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME") or None
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD") or None
    MAIL_SENDER = os.environ.get("MAIL_SENDER") or "Noriūnų J. Černiaus mokykla <noreply@mokykla.lt>"
    MAIL_TIMEOUT = int(os.environ.get("MAIL_TIMEOUT") or 15)
    # „smtp“ – siųsti per serverį; „failai“ – be serverio laiškai įrašomi kaip .eml failai
    MAIL_BACKEND = os.environ.get("MAIL_BACKEND") or ("smtp" if MAIL_SERVER else "failai")
    MAIL_FAILU_KATALOGAS = os.environ.get("MAIL_FAILU_KATALOGAS") or os.path.join(
        BASE_DIR, "duomenys", "laiskai")

    # --- Dokumentai (BD) ---
    # PDF dokumentai saugomi ne static/ kataloge, kad juos būtų galima atsisiųsti tik patikrinus teises
    DOKUMENTU_KATALOGAS = os.environ.get("DOKUMENTU_KATALOGAS") or os.path.join(
        BASE_DIR, "duomenys", "dokumentai")
    MOKYKLOS_REKVIZITAI = os.environ.get("MOKYKLOS_REKVIZITAI") or "Noriūnų k., Kupiškio r. sav."
    MOKYKLOS_VIETOVE = os.environ.get("MOKYKLOS_VIETOVE") or "Noriūnai"
    # Neprivaloma: kelias iki TTF šrifto su lietuviškomis raidėmis (kitaip ieškoma DejaVu arba Arial)
    PDF_SRIFTAS = os.environ.get("PDF_SRIFTAS") or None


class TestConfig(Config):
    """Testinė konfigūracija - in-memory SQLite, jokių išorinių priklausomybių."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "tests", "_uploads_tmp")
    SISTEMOS_ADRESAS = "http://mokykla.test"
    MAIL_SERVER = None
    MAIL_BACKEND = "failai"
    MAIL_FAILU_KATALOGAS = os.path.join(BASE_DIR, "tests", "_uploads_tmp", "laiskai")
    DOKUMENTU_KATALOGAS = os.path.join(BASE_DIR, "tests", "_uploads_tmp", "dokumentai")


class PostgresTestConfig(TestConfig):
    """PostgreSQL testams (pytest -m postgres): atskira duomenų bazė iš TEST_DATABASE_URL.

    Šie testai tikrina tai, ko SQLite neturi: SELECT ... FOR UPDATE SKIP LOCKED,
    jsonb tipą ir migracijų veikimą PostgreSQL. Be TEST_DATABASE_URL jie praleidžiami.
    """
    SQLALCHEMY_DATABASE_URI = normalizuoti_db_adresa(os.environ.get("TEST_DATABASE_URL"))
