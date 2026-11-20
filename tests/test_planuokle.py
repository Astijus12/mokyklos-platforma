"""Fono proceso planuoklės ir worker.py testai (be tikro laukimo ir be tinklo)."""
import pytest
from apscheduler.schedulers.background import BackgroundScheduler

import worker
from models import EilesIrasas, db
from services.planuokle import Planuokle, busenos_patikra


class TestPlanuokle:
    def test_uzduotys_uzregistruojamos(self, app):
        planuokle = Planuokle(app, planuokle=BackgroundScheduler())
        uzduotys = {u.id: u for u in planuokle.registruoti_uzduotis()}
        assert "busenos_patikra" in uzduotys
        assert uzduotys["busenos_patikra"].max_instances == 1

    def test_uzduotis_vykdoma_programos_kontekste(self, app, db_session, tevas):
        db_session.add(EilesIrasas(gavejo_id=tevas.id, kanalas="el_pastas", tema="t", tekstas="t",
                                   unikalus_raktas="r1"))
        db_session.commit()
        planuokle = Planuokle(app, planuokle=BackgroundScheduler())
        apgaubta = planuokle._programos_kontekste(busenos_patikra)
        assert apgaubta() == 1

    def test_uzduoties_klaida_nesustabdo_planuokles(self, app, caplog):
        def luzta():
            raise RuntimeError("bandomoji klaida")

        planuokle = Planuokle(app, planuokle=BackgroundScheduler())
        assert planuokle._programos_kontekste(luzta)() is None
        assert "nepavyko" in caplog.text


class TestWorkerLaukimas:
    def test_grazina_true_kai_schema_naujausia(self, app, monkeypatch):
        monkeypatch.setattr(worker, "ar_schema_naujausia", lambda: True)
        assert worker.laukti_schemos(app, bandymu=1, pauze_s=0) is True

    def test_grazina_false_kai_schema_neatnaujinta(self, app, monkeypatch):
        monkeypatch.setattr(worker, "ar_schema_naujausia", lambda: False)
        assert worker.laukti_schemos(app, bandymu=2, pauze_s=0) is False

    def test_db_klaida_neislaukia_be_galo(self, app, monkeypatch):
        def nepasiekiama():
            raise ConnectionError("DB nepasiekiama")

        monkeypatch.setattr(worker, "ar_schema_naujausia", nepasiekiama)
        assert worker.laukti_schemos(app, bandymu=2, pauze_s=0) is False
