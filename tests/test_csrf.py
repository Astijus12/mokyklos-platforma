"""CSRF apsaugos testai: be žetono POST užklausa atmetama, su žetonu – priimama."""
import re

import pytest

from app import create_app
from config import TestConfig
from models import User, db

pytestmark = pytest.mark.integration


@pytest.fixture
def csrf_klientas(tmp_path):
    class CsrfKonfiguracija(TestConfig):
        WTF_CSRF_ENABLED = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'csrf.db').as_posix()}"

    programa = create_app(CsrfKonfiguracija)
    with programa.app_context():
        db.create_all()
        admin = User(vardas="Admin", pavarde="Testas", email="csrf@test.lt", role="administratorius")
        admin.nustatyti_slaptazodi("admin123")
        db.session.add(admin)
        db.session.commit()
        yield programa.test_client()
        db.session.remove()
        db.engine.dispose()


def _zetonas(html):
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


class TestCsrf:
    def test_prisijungimo_formoje_yra_zetonas(self, csrf_klientas):
        assert 'name="csrf_token"' in csrf_klientas.get("/login").get_data(as_text=True)

    def test_be_zetono_atmetama(self, csrf_klientas):
        atsakymas = csrf_klientas.post("/login", data={"email": "csrf@test.lt", "slaptazodis": "admin123"},
                                       follow_redirects=True)
        assert "Puslapio galiojimas baigėsi" in atsakymas.get_data(as_text=True)
        assert csrf_klientas.get("/dashboard").status_code == 302  # neprisijungta

    def test_su_zetonu_priimama(self, csrf_klientas):
        zetonas = _zetonas(csrf_klientas.get("/login").get_data(as_text=True))
        atsakymas = csrf_klientas.post("/login", data={"email": "csrf@test.lt", "slaptazodis": "admin123",
                                                       "csrf_token": zetonas})
        assert atsakymas.status_code == 302
        assert csrf_klientas.get("/dashboard").status_code == 200

    def test_programine_sasaja_isimta(self, csrf_klientas):
        atsakymas = csrf_klientas.post("/api/v1/auth/token", json={"email": "csrf@test.lt", "slaptazodis": "blogas"})
        assert atsakymas.is_json  # atsako sąsaja, ne CSRF klaida
