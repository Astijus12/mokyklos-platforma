"""Bendros pytest fixtures visiems testams.

Fixtures skopas:
- `app` (session) - vieną kartą per testų sesiją paruošta Flask aplikacija
- `db_session` (function) - kiekvienam testui švari DB per truncate visų lentelių
- `client` (function) - Flask test client
- `admin`, `mokytojas`, `tevas`, `vaikas`, `klase` - patogios vartotojų/objektų fixtures
"""
import importlib.util
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from config import TestConfig
from models import db, User, Klase, Mokinys, AutomatizavimoTaisykle, PranesimoSablonas


def pytest_collection_modifyitems(config, items):
    """Testams iš katalogo tests/postgres automatiškai uždedama žymė „postgres“.

    Taip juos galima paleisti atskirai: pytest -m postgres, arba praleisti:
    pytest -m "not postgres".
    """
    for item in items:
        if "postgres" in item.path.parts:
            item.add_marker(pytest.mark.postgres)


@pytest.fixture(scope="session")
def app():
    """Flask aplikacija testinėje konfigūracijoje - viena visai sesijai."""
    app = create_app(TestConfig)
    with app.app_context():
        yield app


@pytest.fixture(autouse=True)
def db_session(app):
    """Kiekvienam testui - švari DB. autouse=True automatiškai taikoma visur."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client HTTP užklausoms."""
    return app.test_client()


@pytest.fixture
def admin(db_session):
    """Sukuria administratoriaus paskyrą."""
    v = User(vardas="Admin", pavarde="Testas", email="admin@test.lt", role="administratorius")
    v.nustatyti_slaptazodi("admin123")
    db_session.add(v)
    db_session.commit()
    return v


@pytest.fixture
def mokytojas(db_session):
    """Sukuria mokytojo paskyrą."""
    v = User(vardas="Jonas", pavarde="Mokytojas", email="jonas@test.lt", role="mokytojas")
    v.nustatyti_slaptazodi("mokytojas123")
    db_session.add(v)
    db_session.commit()
    return v


@pytest.fixture
def klase(db_session, mokytojas):
    """Sukuria klasę su vadovu (mokytojas)."""
    k = Klase(pavadinimas="5A", mokslo_metai="2025-2026", vadovo_id=mokytojas.id)
    db_session.add(k)
    db_session.commit()
    return k


@pytest.fixture
def vaikas(db_session, klase):
    """Sukuria mokinį klasėje."""
    m = Mokinys(vardas="Petras", pavarde="Vaikaitis", klases_id=klase.id, mokyklos_autobusas=True)
    db_session.add(m)
    db_session.commit()
    return m


@pytest.fixture
def tevas(db_session, vaikas):
    """Sukuria tėvo paskyrą su priskirtu vaiku."""
    t = User(vardas="Petras", pavarde="Tėvas", email="tevas@test.lt", role="tevas")
    t.nustatyti_slaptazodi("tevas123")
    t.vaikai = [vaikas]
    db_session.add(t)
    db_session.commit()
    return t


@pytest.fixture
def prisijunges_admin(client, admin):
    """Test client su prisijungusiu administratoriumi."""
    client.post("/login", data={"email": admin.email, "slaptazodis": "admin123"})
    return client


@pytest.fixture
def prisijunges_tevas(client, tevas):
    """Test client su prisijungusiu tėvu."""
    client.post("/login", data={"email": tevas.email, "slaptazodis": "tevas123"})
    return client


@pytest.fixture
def api_tokenas_admin(db_session, admin):
    """Sugeneruoja API tokeną administratoriui."""
    tokenas = admin.sugeneruoti_api_tokena()
    db_session.commit()
    return tokenas


@pytest.fixture
def api_tokenas_tevas(db_session, tevas):
    """Sugeneruoja API tokeną tėvui."""
    tokenas = tevas.sugeneruoti_api_tokena()
    db_session.commit()
    return tokenas


def ikelti_migracija(failo_vardas):
    """Įkelia migracijos failą kaip modulį (jo pavadinimas prasideda skaičiumi)."""
    kelias = os.path.join(os.path.dirname(__file__), "..", "migrations", "versions", failo_vardas)
    specifikacija = importlib.util.spec_from_file_location(f"migracija_{failo_vardas[:4]}", kelias)
    modulis = importlib.util.module_from_spec(specifikacija)
    specifikacija.loader.exec_module(modulis)
    return modulis


@pytest.fixture
def numatytosios_taisykles(db_session):
    """Numatytieji šablonai ir taisyklės iš migracijos 0004 – testai tikrina tuos pačius tekstus.

    Grąžina žodyną {įvykio tipas: taisyklė}.
    """
    migracija = ikelti_migracija("0004_numatytieji_pranesimai.py")
    sablonai = {}
    for kodas, pavadinimas, tema, tekstas in migracija.SABLONAI:
        sablonai[kodas] = PranesimoSablonas(kodas=kodas, pavadinimas=pavadinimas, tema=tema, tekstas=tekstas)
        db_session.add(sablonai[kodas])
    taisykles = {}
    for pavadinimas, tipas, salyga, gavejai, kanalas, poslinkis, kodas, aktyvi in migracija.TAISYKLES:
        taisykles[tipas] = AutomatizavimoTaisykle(
            pavadinimas=pavadinimas, ivykio_tipas=tipas, salyga=salyga, gavejai=gavejai,
            kanalas=kanalas, poslinkis_d=poslinkis, sablonas=sablonai[kodas], aktyvi=aktyvi,
        )
        db_session.add(taisykles[tipas])
    db_session.commit()
    return taisykles
