"""Bendros pytest fixtures visiems testams.

Fixtures skopas:
- `app` (session) - vieną kartą per testų sesiją paruošta Flask aplikacija
- `db_session` (function) - kiekvienam testui švari DB per truncate visų lentelių
- `client` (function) - Flask test client
- `admin`, `mokytojas`, `tevas`, `vaikas`, `klase` - patogios vartotojų/objektų fixtures
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from config import TestConfig
from models import db, User, Klase, Mokinys


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
