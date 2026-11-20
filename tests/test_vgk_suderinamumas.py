"""Esamų puslapių suderinamumas po VGK duomenų perkėlimo į vgk_atvejai.

Mokinio formos žymė „Gerovės komisija“ dabar kuria, atnaujina arba užbaigia
VGK atvejį (services/vgk.py), o mokinio, tėvų ir programinės sąsajos
puslapiai rodo tuos pačius duomenis kaip iki baigiamojo darbo.
"""
from datetime import date, datetime

import pytest

from models import Mokinys, VgkAtvejis, db
from services.vgk import NUMATYTOJI_PRIEZASTIS, atnaujinti_mokinio_zyme

pytestmark = pytest.mark.integration


class TestVgkZymesPaslauga:
    def test_pazymejus_sukuriamas_uzregistruotas_atvejis(self, db_session, vaikas, mokytojas):
        atvejis = atnaujinti_mokinio_zyme(vaikas, pazymeta=True, pastabos="Dažnai praleidžia pamokas",
                                          naudotojas=mokytojas)
        db_session.commit()
        assert atvejis.busena == VgkAtvejis.UZREGISTRUOTAS
        assert atvejis.pateike_id == mokytojas.id
        assert atvejis.priezastis == "Dažnai praleidžia pamokas"
        assert vaikas.geroves_komisija is True

    def test_be_pastabu_naudojama_numatytoji_priezastis(self, db_session, vaikas):
        atvejis = atnaujinti_mokinio_zyme(vaikas, pazymeta=True)
        db_session.commit()
        assert atvejis.priezastis == NUMATYTOJI_PRIEZASTIS
        assert atvejis.pateike_id is None

    def test_pakartotinai_pazymejus_atnaujinamas_tas_pats_atvejis(self, db_session, vaikas):
        pirmas = atnaujinti_mokinio_zyme(vaikas, pazymeta=True, pastabos="Pirma")
        db_session.commit()
        antras = atnaujinti_mokinio_zyme(vaikas, pazymeta=True, data=date(2026, 11, 3), pastabos="Patikslinta")
        db_session.commit()
        assert pirmas is antras
        assert VgkAtvejis.query.count() == 1
        assert antras.priezastis == "Patikslinta"
        assert antras.sukurta == datetime(2026, 11, 3)

    def test_nuemus_zyme_atvejis_uzbaigiamas(self, db_session, vaikas):
        atvejis = atnaujinti_mokinio_zyme(vaikas, pazymeta=True)
        db_session.commit()
        assert atnaujinti_mokinio_zyme(vaikas, pazymeta=False) is None
        db_session.commit()
        assert atvejis.busena == VgkAtvejis.UZBAIGTAS
        assert atvejis.uzbaigta is not None
        assert vaikas.geroves_komisija is False

    def test_nuemus_zyme_be_atvejo_nieko_nevyksta(self, db_session, vaikas):
        assert atnaujinti_mokinio_zyme(vaikas, pazymeta=False) is None
        assert VgkAtvejis.query.count() == 0


class TestMokinioForma:
    def test_naujas_mokinys_su_vgk_zyme(self, prisijunges_admin, admin, klase):
        atsakymas = prisijunges_admin.post("/mokiniai/naujas", data={
            "klases_id": klase.id, "vardas": "Rokas", "pavarde": "Rokaitis",
            "geroves_komisija": "on", "geroves_komisija_data": "2026-11-10",
            "geroves_komisija_pastabos": "Adaptacijos sunkumai",
        })
        assert atsakymas.status_code == 302
        mokinys = Mokinys.query.filter_by(vardas="Rokas").one()
        atvejis = mokinys.aktyvus_vgk_atvejis
        assert atvejis.priezastis == "Adaptacijos sunkumai"
        assert atvejis.pateike_id == admin.id
        assert mokinys.geroves_komisija_data == date(2026, 11, 10)

    def test_redaguojant_nuimta_zyme_uzbaigia_atveji(self, prisijunges_admin, vaikas, klase):
        db.session.add(VgkAtvejis(mokinio_id=vaikas.id, priezastis="x", busena=VgkAtvejis.SVARSTOMAS))
        db.session.commit()
        atsakymas = prisijunges_admin.post(f"/mokiniai/{vaikas.id}/redaguoti", data={
            "klases_id": klase.id, "vardas": vaikas.vardas, "pavarde": vaikas.pavarde,
        })
        assert atsakymas.status_code == 302
        assert VgkAtvejis.query.one().busena == VgkAtvejis.UZBAIGTAS

    def test_mokinio_puslapis_rodo_vgk_duomenis(self, prisijunges_admin, vaikas):
        db.session.add(VgkAtvejis(mokinio_id=vaikas.id, priezastis="Elgesio sutartis",
                                  busena=VgkAtvejis.SVARSTOMAS, sukurta=datetime(2025, 11, 5, 9, 0)))
        db.session.commit()
        html = prisijunges_admin.get(f"/mokiniai/{vaikas.id}").get_data(as_text=True)
        assert "Svarstymo data: 2025-11-05" in html
        assert "Elgesio sutartis" in html

    def test_sarasas_ir_pradzios_puslapis_veikia(self, prisijunges_admin, vaikas):
        db.session.add(VgkAtvejis(mokinio_id=vaikas.id, priezastis="x"))
        db.session.commit()
        assert prisijunges_admin.get("/mokiniai/").status_code == 200
        assert prisijunges_admin.get("/dashboard").status_code == 200
        assert prisijunges_admin.get("/mokiniai/eksportas").status_code == 200


class TestTevuPortalasIrSasaja:
    def test_sonineje_juostoje_rodoma_teisinga_role(self, prisijunges_tevas):
        html = prisijunges_tevas.get("/tevams/").get_data(as_text=True)
        assert "Tėvas" in html

    def test_programine_sasaja_grazina_vgk_duomenis(self, client, vaikas, api_tokenas_tevas):
        db.session.add(VgkAtvejis(mokinio_id=vaikas.id, priezastis="Konsultacijos",
                                  busena=VgkAtvejis.SVARSTOMAS, sukurta=datetime(2025, 10, 15)))
        db.session.commit()
        atsakymas = client.get(f"/api/v1/children/{vaikas.id}",
                               headers={"Authorization": f"Bearer {api_tokenas_tevas}"})
        assert atsakymas.status_code == 200
        vgk = atsakymas.get_json()["duomenys"]["geroves_komisija"]
        assert vgk == {"aktyvus": True, "data": "2025-10-15", "pastabos": "Konsultacijos"}
