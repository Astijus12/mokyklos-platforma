"""REST API v1 testai - visi endpoint'ai ir saugumas."""
import pytest
import pyotp


pytestmark = pytest.mark.api


def _auth(tokenas):
    return {"Authorization": f"Bearer {tokenas}"}


class TestHealth:
    def test_health_be_autentikacijos(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.get_json()["ok"] is True
        assert r.get_json()["duomenys"]["api_versija"] == "v1"


class TestAuthToken:
    def test_prisijungimas_grazina_tokena(self, client, admin):
        r = client.post("/api/v1/auth/token", json={
            "email": "admin@test.lt",
            "slaptazodis": "admin123",
        })
        assert r.status_code == 200
        d = r.get_json()["duomenys"]
        assert "token" in d
        assert d["vartotojas"]["email"] == "admin@test.lt"

    def test_prisijungimas_su_neteisingu_slaptazodziu(self, client, admin):
        r = client.post("/api/v1/auth/token", json={
            "email": "admin@test.lt",
            "slaptazodis": "blogas",
        })
        assert r.status_code == 401
        assert r.get_json()["ok"] is False

    def test_be_email_grazina_400(self, client):
        r = client.post("/api/v1/auth/token", json={"slaptazodis": "x"})
        assert r.status_code == 400

    def test_su_2fa_be_kodo_grazina_401(self, client, admin, db_session):
        admin.dvfa_paslaptis = pyotp.random_base32()
        admin.dvfa_ijungtas = True
        db_session.commit()

        r = client.post("/api/v1/auth/token", json={
            "email": "admin@test.lt",
            "slaptazodis": "admin123",
        })
        assert r.status_code == 401
        assert "2FA" in r.get_json()["klaida"]

    def test_su_2fa_ir_teisingu_kodu_veikia(self, client, admin, db_session):
        paslaptis = pyotp.random_base32()
        admin.dvfa_paslaptis = paslaptis
        admin.dvfa_ijungtas = True
        db_session.commit()

        r = client.post("/api/v1/auth/token", json={
            "email": "admin@test.lt",
            "slaptazodis": "admin123",
            "dvfa_kodas": pyotp.TOTP(paslaptis).now(),
        })
        assert r.status_code == 200
        assert "token" in r.get_json()["duomenys"]


class TestAutentikacijaEndpoint:
    def test_be_tokeno_grazina_401(self, client):
        r = client.get("/api/v1/me")
        assert r.status_code == 401

    def test_su_neteisingu_tokenu_grazina_401(self, client):
        r = client.get("/api/v1/me", headers=_auth("blogas-tokenas"))
        assert r.status_code == 401

    def test_su_teisingu_tokenu_grazina_200(self, client, api_tokenas_admin):
        r = client.get("/api/v1/me", headers=_auth(api_tokenas_admin))
        assert r.status_code == 200
        assert r.get_json()["duomenys"]["email"] == "admin@test.lt"

    def test_logout_anuliuoja_tokena(self, client, api_tokenas_admin):
        r1 = client.post("/api/v1/auth/logout", headers=_auth(api_tokenas_admin))
        assert r1.status_code == 200

        r2 = client.get("/api/v1/me", headers=_auth(api_tokenas_admin))
        assert r2.status_code == 401


class TestChildrenEndpoint:
    def test_tevas_gauna_savo_vaikus(self, client, api_tokenas_tevas, vaikas):
        r = client.get("/api/v1/children", headers=_auth(api_tokenas_tevas))
        assert r.status_code == 200
        d = r.get_json()["duomenys"]
        assert len(d) == 1
        assert d[0]["id"] == vaikas.id

    def test_admin_negali_kviesti_children(self, client, api_tokenas_admin):
        r = client.get("/api/v1/children", headers=_auth(api_tokenas_admin))
        assert r.status_code == 403

    def test_tevas_gauna_vaiko_detales(self, client, api_tokenas_tevas, vaikas):
        r = client.get(f"/api/v1/children/{vaikas.id}", headers=_auth(api_tokenas_tevas))
        assert r.status_code == 200
        d = r.get_json()["duomenys"]
        assert d["vardas"] == vaikas.vardas
        assert d["mokyklos_autobusas"] is True
        assert d["klases_vadovas"] is not None

    def test_tevas_negali_gauti_svetimo_vaiko(self, client, api_tokenas_tevas):
        r = client.get("/api/v1/children/99999", headers=_auth(api_tokenas_tevas))
        assert r.status_code == 404


class TestAnnouncementsEndpoint:
    def test_admin_mato_visus_skelbimus(self, client, api_tokenas_admin, db_session, admin):
        from models import Skelbimas
        db_session.add_all([
            Skelbimas(pavadinimas="A", turinys="a", matomas_tevams=False, vartotojo_id=admin.id),
            Skelbimas(pavadinimas="B", turinys="b", matomas_tevams=True, vartotojo_id=admin.id),
        ])
        db_session.commit()

        r = client.get("/api/v1/announcements", headers=_auth(api_tokenas_admin))
        assert r.status_code == 200
        assert len(r.get_json()["duomenys"]) == 2

    def test_tevas_mato_tik_matomus(self, client, api_tokenas_tevas, db_session, admin):
        from models import Skelbimas
        db_session.add_all([
            Skelbimas(pavadinimas="Vidinis", turinys="x", matomas_tevams=False, vartotojo_id=admin.id),
            Skelbimas(pavadinimas="Viešas", turinys="y", matomas_tevams=True, vartotojo_id=admin.id),
        ])
        db_session.commit()

        r = client.get("/api/v1/announcements", headers=_auth(api_tokenas_tevas))
        assert r.status_code == 200
        d = r.get_json()["duomenys"]
        assert len(d) == 1
        assert d[0]["pavadinimas"] == "Viešas"


class TestContactsEndpoint:
    def test_tevas_gauna_savo_vaiku_klases_vadovus(self, client, api_tokenas_tevas, klase):
        r = client.get("/api/v1/contacts", headers=_auth(api_tokenas_tevas))
        assert r.status_code == 200
        d = r.get_json()["duomenys"]
        assert len(d) == 1
        assert d[0]["klase"] == "5A"

    def test_admin_gauna_visus_klasiu_vadovus(self, client, api_tokenas_admin, klase):
        r = client.get("/api/v1/contacts", headers=_auth(api_tokenas_admin))
        assert r.status_code == 200
        assert len(r.get_json()["duomenys"]) >= 1
