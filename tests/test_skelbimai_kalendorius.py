"""Skelbimo renginio data -> renginys mokyklos kalendoriuje (services/skelbimai.py)."""
from datetime import date, time

import pytest

from models import EilesIrasas, Renginys, Skelbimas, db

pytestmark = pytest.mark.integration

FORMA = {"pavadinimas": "Kalėdinis koncertas", "turinys": "Kviečiame į koncertą.", "matomas_tevams": "on",
         "kategorija": "renginiai"}


def _skelbti(klientas, **papildomai):
    return klientas.post("/skelbimai/naujas", data={**FORMA, **papildomai})


class TestSkelbimoRenginys:
    def test_su_data_atsiranda_kalendoriuje(self, prisijunges_admin):
        atsakymas = _skelbti(prisijunges_admin, renginio_data="2026-12-18", renginio_laikas="18:00",
                             renginio_vieta="Mokyklos salė")
        assert atsakymas.status_code == 302
        renginys = Skelbimas.query.one().renginys
        assert (renginys.pavadinimas, renginys.pradzios_data, renginys.pradzios_laikas, renginys.vieta,
                renginys.matomas_tevams) == ("Kalėdinis koncertas", date(2026, 12, 18), time(18, 0),
                                             "Mokyklos salė", True)
        kalendorius = prisijunges_admin.get("/kalendorius/?metai=2026&menuo=12").get_data(as_text=True)
        assert "Kalėdinis koncertas" in kalendorius
        detales = prisijunges_admin.get(f"/kalendorius/{renginys.id}").get_data(as_text=True)
        assert "Renginys sukurtas iš skelbimo" in detales

    def test_be_datos_renginio_nera(self, prisijunges_admin):
        _skelbti(prisijunges_admin)
        assert Skelbimas.query.count() == 1
        assert Renginys.query.count() == 0

    def test_netinkama_data_nepraranda_ivestu_duomenu(self, prisijunges_admin):
        html = _skelbti(prisijunges_admin, renginio_data="2026-13-40").get_data(as_text=True)
        assert "Neteisinga renginio data" in html
        assert 'value="Kalėdinis koncertas"' in html
        html = _skelbti(prisijunges_admin, renginio_laikas="18:00").get_data(as_text=True)
        assert "nurodykite ir datą" in html
        assert Skelbimas.query.count() == 0

    def test_redagavimas_keicia_ir_pasalina_rengini(self, prisijunges_admin, numatytosios_taisykles, tevas):
        numatytosios_taisykles["renginys_pakeistas"].aktyvi = True
        db.session.commit()
        _skelbti(prisijunges_admin, renginio_data="2026-12-18")
        skelbimas = Skelbimas.query.one()
        renginio_id = skelbimas.renginys.id

        prisijunges_admin.post(f"/skelbimai/{skelbimas.id}/redaguoti", data={**FORMA, "renginio_data": "2026-12-19"})
        assert db.session.get(Renginys, renginio_id).pradzios_data == date(2026, 12, 19)
        temos = [i.tema for i in EilesIrasas.query]
        assert "Pasikeitė renginio informacija: Kalėdinis koncertas" in temos

        prisijunges_admin.post(f"/skelbimai/{skelbimas.id}/redaguoti", data=FORMA)  # data ištrinta
        assert Renginys.query.count() == 0
        assert Skelbimas.query.count() == 1

    def test_skelbimo_salinimas_pasalina_rengini_ir_atsaukia_priminimus(self, prisijunges_admin, tevas):
        _skelbti(prisijunges_admin, renginio_data="2026-12-18")
        skelbimas = Skelbimas.query.one()
        renginys = skelbimas.renginys
        priminimas = EilesIrasas(gavejo_id=tevas.id, kanalas="el_pastas", tema="t", tekstas="t",
                                 unikalus_raktas=f"renginys-{renginys.id}/renginys_artejantis/t1/g{tevas.id}/el_pastas")
        db.session.add(priminimas)
        db.session.commit()

        prisijunges_admin.post(f"/skelbimai/{skelbimas.id}/salinti")
        assert Skelbimas.query.count() == 0
        assert Renginys.query.count() == 0
        assert db.session.get(EilesIrasas, priminimas.id).busena == EilesIrasas.ATSAUKTAS

    def test_tevai_mato_renginio_data(self, prisijunges_admin, client, tevas):
        _skelbti(prisijunges_admin, renginio_data="2026-12-18", renginio_vieta="Mokyklos salė")
        client.get("/logout")
        client.post("/login", data={"email": tevas.email, "slaptazodis": "tevas123"})
        html = client.get("/tevams/skelbimai").get_data(as_text=True)
        assert "Renginys 2026-12-18" in html and "Mokyklos salė" in html

    def test_skelbimas_tik_darbuotojams_tevu_kalendoriuje_nerodomas(self, prisijunges_admin):
        forma = {k: v for k, v in FORMA.items() if k != "matomas_tevams"}
        prisijunges_admin.post("/skelbimai/naujas", data={**forma, "renginio_data": "2026-12-18"})
        assert Renginys.query.one().matomas_tevams is False
