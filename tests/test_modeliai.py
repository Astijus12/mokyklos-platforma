"""Duomenų modelių testai: User, Mokinys, ryšiai, API tokenai."""
import pytest

from models import User, Mokinys


pytestmark = pytest.mark.modelis


class TestUserSlaptazodis:
    def test_slaptazodzio_hash_saugomas_ne_plaintext(self, db_session):
        v = User(vardas="A", pavarde="B", email="a@b.lt", role="mokytojas")
        v.nustatyti_slaptazodi("labai_slaptas")
        assert v.slaptazodzio_hash != "labai_slaptas"
        assert len(v.slaptazodzio_hash) > 20

    def test_teisingas_slaptazodis_grazina_true(self, admin):
        assert admin.patikrinti_slaptazodi("admin123") is True

    def test_neteisingas_slaptazodis_grazina_false(self, admin):
        assert admin.patikrinti_slaptazodi("blogas") is False


class TestUserPropertys:
    def test_pilnas_vardas(self, admin):
        assert admin.pilnas_vardas == "Admin Testas"

    def test_pilnas_vardas_be_pavardes(self, db_session):
        v = User(vardas="ADMIN", pavarde="", email="x@y.lt", role="administratorius")
        v.nustatyti_slaptazodi("x")
        assert v.pilnas_vardas == "ADMIN"

    def test_inicialai(self, admin):
        assert admin.inicialai == "AT"

    def test_yra_administratorius(self, admin, mokytojas, tevas):
        assert admin.yra_administratorius is True
        assert mokytojas.yra_administratorius is False
        assert tevas.yra_administratorius is False

    def test_yra_tevas(self, admin, tevas):
        assert tevas.yra_tevas is True
        assert admin.yra_tevas is False

    def test_yra_mokytojas(self, mokytojas, admin):
        assert mokytojas.yra_mokytojas is True
        assert admin.yra_mokytojas is False


class TestTevoVaikoRysys:
    def test_tevas_turi_vaika(self, tevas, vaikas):
        assert vaikas in tevas.vaikai.all()
        assert tevas.vaikai.count() == 1

    def test_vaikas_turi_teva(self, tevas, vaikas):
        assert tevas in vaikas.tevai.all()

    def test_priskirti_kelis_vaikus(self, db_session, tevas, klase):
        m2 = Mokinys(vardas="Antras", pavarde="Vaikas", klases_id=klase.id)
        db_session.add(m2)
        db_session.commit()
        tevas.vaikai.append(m2)
        db_session.commit()
        assert tevas.vaikai.count() == 2

    def test_vienas_vaikas_gali_tureti_kelis_tevus(self, db_session, tevas, vaikas):
        t2 = User(vardas="Motina", pavarde="Testinė", email="motina@test.lt", role="tevas")
        t2.nustatyti_slaptazodi("t")
        t2.vaikai = [vaikas]
        db_session.add(t2)
        db_session.commit()
        assert vaikas.tevai.count() == 2


class TestApiTokenas:
    def test_generavimas_grazina_tekstini_tokena(self, admin, db_session):
        tokenas = admin.sugeneruoti_api_tokena()
        db_session.commit()
        assert isinstance(tokenas, str)
        assert len(tokenas) >= 32

    def test_saugomas_hash_ne_plaintext(self, admin, db_session):
        tokenas = admin.sugeneruoti_api_tokena()
        db_session.commit()
        assert admin.api_token_hash != tokenas
        assert len(admin.api_token_hash) == 64

    def test_rasti_pagal_teisinga_tokena(self, admin, db_session):
        tokenas = admin.sugeneruoti_api_tokena()
        db_session.commit()
        rastas = User.rasti_pagal_api_tokena(tokenas)
        assert rastas is not None
        assert rastas.id == admin.id

    def test_rasti_pagal_neteisinga_tokena_grazina_none(self, admin, db_session):
        admin.sugeneruoti_api_tokena()
        db_session.commit()
        assert User.rasti_pagal_api_tokena("blogas-tokenas") is None

    def test_anuliavimas_isvalo_lauka(self, admin, db_session):
        admin.sugeneruoti_api_tokena()
        db_session.commit()
        admin.anuliuoti_api_tokena()
        db_session.commit()
        assert admin.api_token_hash is None

    def test_naujas_tokenas_anuliuoja_seno(self, admin, db_session):
        senas = admin.sugeneruoti_api_tokena()
        db_session.commit()
        naujas = admin.sugeneruoti_api_tokena()
        db_session.commit()
        assert User.rasti_pagal_api_tokena(senas) is None
        assert User.rasti_pagal_api_tokena(naujas).id == admin.id


class TestMokinys:
    def test_pilnas_vardas(self, vaikas):
        assert vaikas.pilnas_vardas == "Petras Vaikaitis"

    def test_inicialai(self, vaikas):
        assert vaikas.inicialai == "PV"

    def test_priklauso_klasei(self, vaikas, klase):
        assert vaikas.klase.id == klase.id
        assert vaikas in klase.mokiniai
