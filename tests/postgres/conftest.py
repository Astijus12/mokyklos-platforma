"""PostgreSQL testų aplinka.

Šie fiksatoriai pakeičia pagrindinio conftest.py fiksatorius „app“ ir „db_session“
tik šio katalogo testams (kiti fiksatoriai, pvz., admin, tevas, vaikas, veikia kaip įprasta):
- app – programa, prijungta prie TEST_DATABASE_URL. Testų sesijos pradžioje schema
  sukuriama iš naujo migracijomis, todėl kartu patikrinamos ir migracijos PostgreSQL;
- db_session – po kiekvieno testo visų lentelių duomenys ištrinami (TRUNCATE).

Jei TEST_DATABASE_URL nenurodytas arba PostgreSQL nepasiekiamas, testai praleidžiami.
Saugumo sumetimais duomenų bazės pavadinime turi būti žodis „test“, kad testai
netyčia neištrintų kūrimo duomenų bazės.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import create_app
from config import PostgresTestConfig
from db_atnaujinimas import sukurti_schema_is_naujo
from models import db


def _patikrinti_adresa(adresas):
    """Grąžina priežastį, dėl kurios testų negalima vykdyti, arba None."""
    if not adresas:
        return "nenurodytas TEST_DATABASE_URL (žr. .env.example)"
    url = make_url(adresas)
    if not url.drivername.startswith("postgresql"):
        return "TEST_DATABASE_URL turi būti PostgreSQL adresas"
    if "test" not in (url.database or ""):
        return "testų duomenų bazės pavadinime turi būti žodis „test“ (pvz., mokykla_test)"
    try:
        variklis = create_engine(adresas)
        with variklis.connect():
            pass
        variklis.dispose()
    except Exception as klaida:
        return f"PostgreSQL nepasiekiamas: {str(klaida).strip().splitlines()[0]}"
    return None


@pytest.fixture(scope="session")
def app():
    priezastis = _patikrinti_adresa(os.environ.get("TEST_DATABASE_URL"))
    if priezastis:
        pytest.skip(f"PostgreSQL testai praleidžiami: {priezastis}")

    programa = create_app(PostgresTestConfig)
    with programa.app_context():
        sukurti_schema_is_naujo()
        yield programa
        db.session.remove()
        db.engine.dispose()


@pytest.fixture(autouse=True)
def db_session(app):
    yield db.session
    db.session.remove()
    lenteles = ", ".join(lentele.name for lentele in db.metadata.sorted_tables)
    with db.engine.begin() as rysys:
        rysys.execute(text(f"TRUNCATE {lenteles} RESTART IDENTITY CASCADE"))
