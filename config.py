"""Konfigūracijos failas - čia laikomi visi nustatymai."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Kūrimo aplinkoje nustatymai (pvz., DATABASE_URL vietiniam PostgreSQL) laikomi
# faile .env (jis neįtraukiamas į git). Jau nustatyti aplinkos kintamieji
# (Docker, Render) neperrašomi.
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "demo-slaptas-raktas-pakeisk-pries-naudojant")

    DATABASE_URL = os.environ.get("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{os.path.join(BASE_DIR, 'mokykla.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}


class TestConfig(Config):
    """Testinė konfigūracija - in-memory SQLite, jokių išorinių priklausomybių."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "tests", "_uploads_tmp")


class PostgresTestConfig(TestConfig):
    """PostgreSQL testams (pytest -m postgres): atskira duomenų bazė iš TEST_DATABASE_URL.

    Šie testai tikrina tai, ko SQLite neturi: SELECT ... FOR UPDATE SKIP LOCKED,
    jsonb tipą ir migracijų veikimą PostgreSQL. Be TEST_DATABASE_URL jie praleidžiami.
    """
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL")
