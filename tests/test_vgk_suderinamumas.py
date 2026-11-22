"""Esamų puslapių elgsena po VGK modulio įdiegimo (NFR-06).

VGK duomenys (žymės, atvejai, pastabos) mokinių sąraše, kortelėje, eksporte ir
tėvų portale rodomi tik komisijos nariams ir administratoriui. Mokinio formoje
senos VGK varnelės nebėra – kreipimasis pateikiamas VGK modulyje. Programinė
sąsaja tėvams VGK duomenų neteikia.
"""
import pytest

from models import User, VgkAtvejis, db

pytestmark = pytest.mark.integration


@pytest.fixture
def aktyvus_atvejis(db_session, vaikas, mokytojas):
    atvejis = VgkAtvejis(mokinio_id=vaikas.id, pateike_id=mokytojas.id, priezastis="Elgesio sutartis",
                         busena=VgkAtvejis.SVARSTOMAS)
    db_session.add(atvejis)
    db_session.commit()
    return atvejis


@pytest.fixture
def prisijunges_mokytojas(client, mokytojas):
    client.post("/login", data={"email": mokytojas.email, "slaptazodis": "mokytojas123"})
    return client


def _html(atsakymas):
    return atsakymas.get_data(as_text=True)


class TestMatomumas:
    def test_administratorius_mato_vgk_kortele(self, prisijunges_admin, vaikas, aktyvus_atvejis):
        html = _html(prisijunges_admin.get(f"/mokiniai/{vaikas.id}"))
        assert f"Atvejis {aktyvus_atvejis.numeris}" in html
        assert "Svarstomas" in html

    def test_paprastas_mokytojas_vgk_duomenu_nemato(self, prisijunges_mokytojas, vaikas, aktyvus_atvejis):
        html = _html(prisijunges_mokytojas.get(f"/mokiniai/{vaikas.id}"))
        assert f"Atvejis {aktyvus_atvejis.numeris}" not in html
        assert "matomi tik komisijos nariams" in html
        assert "Pateikti kreipimąsi" in html

    def test_saraso_zyme_tik_nariams(self, prisijunges_mokytojas, vaikas, aktyvus_atvejis, mokytojas):
        assert 'title="Svarstomas Vaiko gerovės komisijoje"' not in _html(prisijunges_mokytojas.get("/mokiniai/"))
        mokytojas.vgk_pareigos = "narys"
        db.session.commit()
        assert 'title="Svarstomas Vaiko gerovės komisijoje"' in _html(prisijunges_mokytojas.get("/mokiniai/"))

    def test_administratoriaus_eksporte_vgk_stulpeliai_yra(self, prisijunges_admin, vaikas, aktyvus_atvejis):
        assert "Gerovės komisija" in prisijunges_admin.get("/mokiniai/eksportas").get_data(as_text=True)

    def test_mokytojo_eksporte_vgk_nera(self, prisijunges_mokytojas, vaikas, aktyvus_atvejis):
        assert "Gerovės komisija" not in prisijunges_mokytojas.get("/mokiniai/eksportas").get_data(as_text=True)
        assert prisijunges_mokytojas.get("/mokiniai/eksportas-xlsx").status_code == 200

    def test_tevu_portale_vgk_nerodoma(self, prisijunges_tevas, vaikas, aktyvus_atvejis):
        assert "Elgesio sutartis" not in _html(prisijunges_tevas.get(f"/tevams/vaikas/{vaikas.id}"))

    def test_programine_sasaja_vgk_duomenu_neteikia(self, client, vaikas, api_tokenas_tevas, aktyvus_atvejis):
        atsakymas = client.get(f"/api/v1/children/{vaikas.id}",
                               headers={"Authorization": f"Bearer {api_tokenas_tevas}"})
        assert atsakymas.status_code == 200
        assert "geroves_komisija" not in atsakymas.get_json()["duomenys"]

    def test_pradzios_puslapis_veikia(self, prisijunges_admin, aktyvus_atvejis):
        assert "VGK atvejai" in _html(prisijunges_admin.get("/dashboard"))


class TestMokinioForma:
    def test_formoje_nebera_vgk_varneles(self, prisijunges_admin, vaikas):
        html = _html(prisijunges_admin.get(f"/mokiniai/{vaikas.id}/redaguoti"))
        assert 'name="geroves_komisija"' not in html
        assert "pateikti kreipimąsi dėl šio mokinio" in html

    def test_mokinio_redagavimas_neliecia_atveju(self, prisijunges_admin, vaikas, klase, aktyvus_atvejis):
        atsakymas = prisijunges_admin.post(f"/mokiniai/{vaikas.id}/redaguoti", data={
            "klases_id": klase.id, "vardas": vaikas.vardas, "pavarde": "Naujapavardis",
        })
        assert atsakymas.status_code == 302
        assert db.session.get(VgkAtvejis, aktyvus_atvejis.id).busena == VgkAtvejis.SVARSTOMAS


class TestRoliuPavadinimai:
    def test_sonineje_juostoje_rodoma_teisinga_role(self, prisijunges_tevas):
        assert "Tėvas" in _html(prisijunges_tevas.get("/tevams/"))

    def test_administratorius_priskiria_vgk_pareigas(self, prisijunges_admin, mokytojas):
        prisijunges_admin.post(f"/vartotojai/{mokytojas.id}/redaguoti", data={
            "vardas": mokytojas.vardas, "pavarde": mokytojas.pavarde, "email": mokytojas.email,
            "role": "mokytojas", "vgk_pareigos": "sekretorius",
        })
        assert db.session.get(User, mokytojas.id).vgk_pareigos == "sekretorius"
