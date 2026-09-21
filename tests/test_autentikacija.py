"""Autentikacijos, atsijungimo, rolių apsaugos testai."""
import pytest
import pyotp

from models import db


pytestmark = pytest.mark.auth


class TestPrisijungimas:
    def test_login_puslapis_grazina_200(self, client):
        r = client.get("/login")
        assert r.status_code == 200
        assert b"Prisijungimas" in r.data or b"prisijungimas" in r.data.lower()

    def test_teisingi_duomenys_admin_nukreipia_i_dashboard(self, client, admin):
        r = client.post("/login", data={"email": "admin@test.lt", "slaptazodis": "admin123"})
        assert r.status_code == 302
        assert r.headers["Location"].endswith("/dashboard")

    def test_teisingi_duomenys_tevas_nukreipia_i_tevu_portala(self, client, tevas):
        r = client.post("/login", data={"email": "tevas@test.lt", "slaptazodis": "tevas123"})
        assert r.status_code == 302
        assert r.headers["Location"].endswith("/tevams/")

    def test_neteisingas_slaptazodis(self, client, admin):
        r = client.post("/login", data={"email": "admin@test.lt", "slaptazodis": "blogas"})
        assert r.status_code == 200
        assert "Neteisingas".encode("utf-8") in r.data

    def test_nesamas_vartotojas(self, client):
        r = client.post("/login", data={"email": "nera@test.lt", "slaptazodis": "x"})
        assert r.status_code == 200
        assert "Neteisingas".encode("utf-8") in r.data

    def test_atsijungimas(self, prisijunges_admin):
        r = prisijunges_admin.get("/logout")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]


class TestRoliuApsauga:
    def test_neprisijunges_vartotojas_nukreiptas_i_login(self, client):
        r = client.get("/dashboard")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_admin_gali_pasiekti_dashboarda(self, prisijunges_admin):
        r = prisijunges_admin.get("/dashboard")
        assert r.status_code == 200

    def test_tevas_negali_pasiekti_dashboardo(self, prisijunges_tevas):
        r = prisijunges_tevas.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert "/tevams/" in r.headers["Location"]

    def test_tevas_negali_pasiekti_mokiniu_saraso(self, prisijunges_tevas):
        r = prisijunges_tevas.get("/mokiniai/", follow_redirects=False)
        assert r.status_code == 302
        assert "/tevams/" in r.headers["Location"]

    def test_tevas_negali_pasiekti_klasiu(self, prisijunges_tevas):
        r = prisijunges_tevas.get("/klases/", follow_redirects=False)
        assert r.status_code == 302

    def test_tevas_negali_pasiekti_vartotoju_saraso(self, prisijunges_tevas):
        r = prisijunges_tevas.get("/vartotojai/", follow_redirects=True)
        assert "/tevams/".encode() in r.request.path.encode() or "tik administratoriams".encode("utf-8") in r.data or b"tevu" in r.data or "tėvams".encode("utf-8") in r.data


class TestTevuPortalas:
    def test_tevas_pasiekia_savo_dashboarda(self, prisijunges_tevas):
        r = prisijunges_tevas.get("/tevams/")
        assert r.status_code == 200
        assert "Sveiki".encode("utf-8") in r.data

    def test_tevas_mato_savo_vaika(self, prisijunges_tevas, vaikas):
        r = prisijunges_tevas.get(f"/tevams/vaikas/{vaikas.id}")
        assert r.status_code == 200
        assert vaikas.vardas.encode() in r.data

    def test_tevas_negali_pasiekti_svetimo_vaiko(self, prisijunges_tevas):
        r = prisijunges_tevas.get("/tevams/vaikas/99999")
        assert r.status_code == 404

    def test_ne_tevas_negali_pasiekti_tevu_portalo(self, prisijunges_admin):
        r = prisijunges_admin.get("/tevams/", follow_redirects=False)
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]


class TestDvfaAutentikacija:
    def test_su_ijungtu_2fa_login_nukreipia_i_patvirtinima(self, client, admin, db_session):
        admin.dvfa_paslaptis = pyotp.random_base32()
        admin.dvfa_ijungtas = True
        db_session.commit()

        r = client.post("/login", data={"email": "admin@test.lt", "slaptazodis": "admin123"})
        assert r.status_code == 302
        assert "/saugumas/2fa/patvirtinti" in r.headers["Location"]

    def test_2fa_kodu_patvirtinimas_prisijungia(self, client, admin, db_session):
        paslaptis = pyotp.random_base32()
        admin.dvfa_paslaptis = paslaptis
        admin.dvfa_ijungtas = True
        db_session.commit()

        client.post("/login", data={"email": "admin@test.lt", "slaptazodis": "admin123"})
        kodas = pyotp.TOTP(paslaptis).now()

        r = client.post("/saugumas/2fa/patvirtinti", data={"kodas": kodas})
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]

    def test_neteisingas_2fa_kodas_neleidziamas(self, client, admin, db_session):
        admin.dvfa_paslaptis = pyotp.random_base32()
        admin.dvfa_ijungtas = True
        db_session.commit()

        client.post("/login", data={"email": "admin@test.lt", "slaptazodis": "admin123"})
        r = client.post("/saugumas/2fa/patvirtinti", data={"kodas": "000000"})
        assert r.status_code == 200
        assert "Neteisingas".encode("utf-8") in r.data


class TestSkelbimuMatomumas:
    def test_tevas_mato_tik_matomus_skelbimus(self, prisijunges_tevas, db_session, admin):
        from models import Skelbimas
        s1 = Skelbimas(pavadinimas="Vidinis", turinys="x", matomas_tevams=False, vartotojo_id=admin.id)
        s2 = Skelbimas(pavadinimas="Viešas", turinys="y", matomas_tevams=True, vartotojo_id=admin.id)
        db_session.add_all([s1, s2])
        db_session.commit()

        r = prisijunges_tevas.get("/tevams/skelbimai")
        assert r.status_code == 200
        assert "Viešas".encode("utf-8") in r.data
        assert b"Vidinis" not in r.data
