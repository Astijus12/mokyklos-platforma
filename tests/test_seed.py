"""Demonstraciniai duomenys (seed.py): visi moduliai užpildyti, failai sukurti, tikri laiškai nesiunčiami.

Render'yje šie duomenys kuriami kiekvieną kartą paleidžiant svetainę, todėl scenarijus turi veikti be klaidų.
"""
import os
import re
from datetime import date

import pytest

import seed
from app import create_app
from config import TestConfig
from models import (Diplomas, Dokumentas, EilesIrasas, ImportoSesija, PazymosPrasymas, Pranesimas, Renginys,
                    Skelbimas, User, VgkAtvejis, VgkPosedis, db)
from services.dokumentai import kelias_diske

pytestmark = pytest.mark.migracijos


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    katalogas = tmp_path_factory.mktemp("demo")

    class DemoKonfiguracija(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(katalogas / 'demo.db').as_posix()}"
        UPLOAD_FOLDER = str(katalogas / "ikelti")
        DOKUMENTU_KATALOGAS = str(katalogas / "dokumentai")
        MAIL_FAILU_KATALOGAS = str(katalogas / "laiskai")
        MAIL_BACKEND = "smtp"                 # net nustačius SMTP serverį ...
        MAIL_SERVER = "smtp.netikras.test"    # ... demonstraciniai laiškai įrašomi į failus

    programa = create_app(DemoKonfiguracija)
    with programa.app_context():
        seed.uzpildyti_db(naudoti_esama_app=True, isvalyti=True)
        yield programa
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def demo_kontekstas(demo):
    with demo.app_context():
        yield demo


@pytest.mark.parametrize("aplinka, tiketina", [
    ({}, False),
    ({"RENDER": "true"}, True),
    ({"RENDER": "true", "DEMO_SVETAINE": "0"}, False),
    ({"DEMO_SVETAINE": "1"}, True),
], ids=["kurimo_aplinka", "render", "render_isjungta", "nurodyta_tiesiogiai"])
def test_ar_demo_svetaine(aplinka, tiketina):
    assert seed.ar_demo_svetaine(aplinka) is tiketina


def test_data_tekstu():
    assert seed.data_tekstu(date(2026, 12, 18)) == "gruodžio 18 d."
    assert seed.mokslo_metai(date(2026, 11, 22)) == "2026-2027"
    assert seed.mokslo_metai(date(2027, 1, 20)) == "2026-2027"


class TestDemonstraciniaiDuomenys:
    def test_skelbimai_su_renginiais_kalendoriuje(self, demo_kontekstas):
        assert Skelbimas.query.count() == 7
        assert sum(1 for s in Skelbimas.query if s.renginys) == 6
        assert Renginys.query.count() >= 9

    def test_vgk_posedis_ateityje_su_kvietimais(self, demo_kontekstas):
        suplanuotas = VgkPosedis.query.filter_by(busena=VgkPosedis.SUPLANUOTAS).one()
        assert suplanuotas.data > date.today()
        assert len(suplanuotas.dalyviai) == 4  # pirmininkė, sekretorius, mama ir kviestinė psichologė
        assert VgkPosedis.query.filter_by(busena=VgkPosedis.IVYKES).one().protokolas is not None
        assert {a.busena for a in VgkAtvejis.query} == {VgkAtvejis.TAIKOMOS_PRIEMONES, VgkAtvejis.SVARSTOMAS,
                                                       VgkAtvejis.UZREGISTRUOTAS}

    def test_pazymos_dokumentai_ir_diplomai_su_failais(self, demo_kontekstas):
        assert sorted(p.busena for p in PazymosPrasymas.query) == sorted(
            [PazymosPrasymas.IVYKDYTAS, PazymosPrasymas.ATMESTAS, PazymosPrasymas.PATEIKTAS])
        assert {d.tipas for d in Dokumentas.query} == {"PR", "PZ", "AT"}
        assert all(os.path.exists(kelias_diske(d)) for d in Dokumentas.query)
        diplomai = Diplomas.query.all()
        assert len(diplomai) == 3
        assert all(os.path.exists(os.path.join(demo_kontekstas.config["UPLOAD_FOLDER"], d.failo_kelias))
                   for d in diplomai)

    def test_importas_ivykdytas(self, demo_kontekstas):
        sesija = ImportoSesija.query.one()
        assert sesija.busena == ImportoSesija.IMPORTUOTA
        assert (sesija.tinkamu_sk, sesija.klaidu_sk) == (3, 1)

    def test_prisijungimo_puslapio_naudotojai_yra_demonstraciniuose_duomenyse(self, demo_kontekstas):
        html = demo_kontekstas.test_client().get("/login").get_data(as_text=True)
        poros = re.findall(r"uzpildyti\('([^']+)', '([^']+)'\)", html)
        assert [el_pastas for el_pastas, _ in poros] == [
            "admin@mokykla.lt", "jonas@mokykla.lt", "ona@mokykla.lt", "tevas@demo.lt", "lina.griciene@demo.lt"]
        for el_pastas, slaptazodis in poros:
            assert User.query.filter_by(email=el_pastas).one().patikrinti_slaptazodi(slaptazodis)
        assert "Komisijos pirmininkė" in html and "Administratorius" in html

    def test_pranesimai_issiusti_i_failus(self, demo_kontekstas):
        assert EilesIrasas.query.filter_by(busena=EilesIrasas.LAUKIA).count() == 0
        assert EilesIrasas.query.filter_by(busena=EilesIrasas.ISSIUSTAS).count() > 0
        assert EilesIrasas.query.filter_by(busena=EilesIrasas.NEPAVYKO).count() == 1
        assert Pranesimas.query.count() > 0
        assert os.listdir(demo_kontekstas.config["MAIL_FAILU_KATALOGAS"])  # .eml failai, ne SMTP
