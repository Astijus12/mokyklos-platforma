"""Dokumentų modulio testai (FR-D01–FR-D08, NFR-11).

Generatoriai ir numeracija, SHA-256 vientisumas, atsisiuntimo teisės, pažymų
prašymų eiga su pranešimais, ataskaitos ir mėnesio suvestinė, puslapiai.
"""
from datetime import date, time

import pytest

from models import (
    Dokumentas,
    DokumentuSkaitiklis,
    EilesIrasas,
    Mokinys,
    PazymosPrasymas,
    User,
    VgkAtvejis,
    VgkDalyvis,
    VgkPosedis,
    VgkPriemone,
    VgkSvarstymas,
    db,
)
from services.dokumentai import (
    AtaskaitosGeneratorius,
    PazymosGeneratorius,
    ProtokoloGeneratorius,
    kelias_diske,
    tikrinti_vientisuma,
)
from services.pazymos import (
    PrasymoKlaida,
    ankstesnis_menuo,
    atmesti_prasyma,
    ataskaitos_duomenys,
    gali_atsisiusti,
    laikotarpio_pavadinimas,
    parengti_ataskaita,
    pateikti_prasyma,
    patvirtinti_prasyma,
    sukurti_menesio_suvestine,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def dokumentu_katalogas(app, tmp_path):
    """PDF failai testuose įrašomi į laikiną katalogą."""
    senas = app.config["DOKUMENTU_KATALOGAS"]
    app.config["DOKUMENTU_KATALOGAS"] = str(tmp_path / "dokumentai")
    yield tmp_path / "dokumentai"
    app.config["DOKUMENTU_KATALOGAS"] = senas


def _naudotojas(vardas, role, email, **papildomai):
    naudotojas = User(vardas=vardas, pavarde="Testas", email=email, role=role, **papildomai)
    naudotojas.nustatyti_slaptazodi("slaptas123")
    db.session.add(naudotojas)
    db.session.commit()
    return naudotojas


def _pazyma(mokinys, sukure=None, paskirtis="Darbdaviui"):
    dokumentas = PazymosGeneratorius().parengti({"mokinys": mokinys, "paskirtis": paskirtis},
                                                mokinys=mokinys, sukure=sukure)
    db.session.commit()
    return dokumentas


def _posedis_su_svarstymu(mokinys, atsakingas, narys):
    posedis = VgkPosedis(data=date(2026, 12, 8), laikas=time(14, 0), vieta="Mokytojų kambarys",
                         busena=VgkPosedis.IVYKES)
    svarstymas = VgkSvarstymas(atvejis=VgkAtvejis(mokinio_id=mokinys.id, priezastis="Lankomumo <sunkumai> & kt."),
                               eiles_nr=1, nutarimas="Skirti socialinio pedagogo konsultacijas.")
    posedis.svarstymai.append(svarstymas)
    posedis.dalyviai.append(VgkDalyvis(vartotojo_id=narys.id, vardas_pavarde=narys.pilnas_vardas,
                                       vaidmuo="pirmininkas", dalyvavo=True, pasizadejimas=True))
    db.session.add(posedis)
    svarstymas.priemones.append(VgkPriemone(atsakingo_id=atsakingas.id, aprasymas="Konsultacijos kas savaitę",
                                            terminas=date(2026, 12, 20)))
    db.session.commit()
    return posedis


class TestGeneratoriai:
    def test_pazyma_su_numeriu_failu_ir_kontroline_suma(self, admin, vaikas):
        dokumentas = _pazyma(vaikas, sukure=admin)
        metai = date.today().year
        assert dokumentas.numeris == f"PZ-{metai}-0001"
        assert (dokumentas.tipas, dokumentas.mokinio_id, dokumentas.sukure_id) == ("PZ", vaikas.id, admin.id)
        with open(kelias_diske(dokumentas), "rb") as failas:
            assert failas.read(5) == b"%PDF-"
        assert len(dokumentas.sha256) == 64
        assert tikrinti_vientisuma(dokumentas)

    def test_numeriai_nuoseklus_ir_atskiri_pagal_tipa(self, admin, vaikas, mokytojas):
        metai = date.today().year
        numeriai = [_pazyma(vaikas).numeris for _ in range(3)]
        assert numeriai == [f"PZ-{metai}-0001", f"PZ-{metai}-0002", f"PZ-{metai}-0003"]
        protokolas = ProtokoloGeneratorius().parengti({"posedis": _posedis_su_svarstymu(vaikas, mokytojas, admin)})
        db.session.commit()
        assert protokolas.numeris == f"PR-{metai}-0001"
        assert db.session.get(DokumentuSkaitiklis, ("PZ", metai)).paskutinis_nr == 3

    def test_pakeistas_failas_aptinkamas(self, vaikas):
        """FR-D05: SHA-256 leidžia patikrinti, ar failas nebuvo pakeistas."""
        dokumentas = _pazyma(vaikas)
        with open(kelias_diske(dokumentas), "ab") as failas:
            failas.write(b"pakeitimas")
        assert tikrinti_vientisuma(dokumentas) is False

    def test_dingusio_failo_vientisumas_neigiamas(self, vaikas):
        dokumentas = _pazyma(vaikas)
        dokumentas.failo_kelias = "nera/tokio.pdf"
        assert tikrinti_vientisuma(dokumentas) is False

    def test_protokolas_ir_ataskaita_sugeneruojami(self, admin, mokytojas, vaikas):
        protokolas = ProtokoloGeneratorius().parengti({"posedis": _posedis_su_svarstymu(vaikas, mokytojas, admin)})
        ataskaita = AtaskaitosGeneratorius().parengti(
            {"nuo": date(2026, 11, 1), "iki": date(2026, 11, 30),
             "statistika": ataskaitos_duomenys(date(2026, 11, 1), date(2026, 11, 30))})
        db.session.commit()
        for dokumentas in (protokolas, ataskaita):
            assert tikrinti_vientisuma(dokumentas)
        assert protokolas.tipo_pavadinimas == "VGK posėdžio protokolas"


class TestAtsisiuntimoTeises:
    def test_teises_pagal_role(self, admin, mokytojas, tevas, vaikas, klase):
        kitas_vaikas = Mokinys(vardas="Kitas", pavarde="Vaikas", klases_id=klase.id)
        db.session.add(kitas_vaikas)
        db.session.commit()
        pazyma = _pazyma(vaikas)
        svetima = _pazyma(kitas_vaikas)
        narys = _naudotojas("Ona", "mokytojas", "ona@test.lt", vgk_pareigos="narys")
        protokolas = ProtokoloGeneratorius().parengti({"posedis": _posedis_su_svarstymu(vaikas, mokytojas, narys)})
        db.session.commit()

        assert gali_atsisiusti(admin, pazyma) and gali_atsisiusti(admin, protokolas)
        assert gali_atsisiusti(tevas, pazyma)
        assert not gali_atsisiusti(tevas, svetima)
        assert not gali_atsisiusti(tevas, protokolas)
        assert not gali_atsisiusti(mokytojas, pazyma)
        assert not gali_atsisiusti(mokytojas, protokolas)  # ne komisijos narys
        assert gali_atsisiusti(narys, protokolas)


class TestPrasymuEiga:
    def test_pateikus_pranesama_administratoriui(self, numatytosios_taisykles, admin, tevas, vaikas):
        prasymas = pateikti_prasyma(tevas, vaikas, "Darbdaviui", "du egzemplioriai")
        assert prasymas.busena == PazymosPrasymas.PATEIKTAS
        assert prasymas.paskirtis == "Darbdaviui (du egzemplioriai)"
        irasas = EilesIrasas.query.one()
        assert (irasas.gavejo_id, irasas.kanalas) == (admin.id, "sistema")
        assert vaikas.pilnas_vardas in irasas.tema

    def test_svetimo_vaiko_pazymos_uzsakyti_negalima(self, tevas, klase):
        svetimas = Mokinys(vardas="Svetimas", pavarde="Vaikas", klases_id=klase.id)
        db.session.add(svetimas)
        db.session.commit()
        with pytest.raises(PrasymoKlaida):
            pateikti_prasyma(tevas, svetimas, "Darbdaviui")
        with pytest.raises(PrasymoKlaida):
            pateikti_prasyma(tevas, None, "Darbdaviui")

    def test_be_paskirties_negalima(self, tevas, vaikas):
        with pytest.raises(PrasymoKlaida):
            pateikti_prasyma(tevas, vaikas, "  ")

    def test_patvirtinus_sugeneruojama_pazyma_ir_pranesama_tevui(self, numatytosios_taisykles, admin, tevas,
                                                                   vaikas):
        prasymas = pateikti_prasyma(tevas, vaikas, "Pateikti „Sodrai“")
        dokumentas = patvirtinti_prasyma(prasymas, admin)
        assert prasymas.busena == PazymosPrasymas.IVYKDYTAS
        assert prasymas.dokumentas == dokumentas and prasymas.nagrinejo_id == admin.id
        tevo_laiskas = EilesIrasas.query.filter_by(gavejo_id=tevas.id, kanalas="el_pastas").one()
        assert dokumentas.numeris in tevo_laiskas.tekstas
        assert "/dokumentai/mano-pazymos" in tevo_laiskas.tekstas
        with pytest.raises(PrasymoKlaida):
            patvirtinti_prasyma(prasymas, admin)  # antrą kartą – ne

    def test_atmetimas_su_priezastimi(self, numatytosios_taisykles, admin, tevas, vaikas):
        prasymas = pateikti_prasyma(tevas, vaikas, "Darbdaviui")
        with pytest.raises(PrasymoKlaida):
            atmesti_prasyma(prasymas, admin, "")
        atmesti_prasyma(prasymas, admin, "Mokinys išvykęs iš mokyklos")
        assert prasymas.busena == PazymosPrasymas.ATMESTAS
        tevo_laiskas = EilesIrasas.query.filter_by(gavejo_id=tevas.id, kanalas="el_pastas").one()
        assert "Mokinys išvykęs iš mokyklos" in tevo_laiskas.tekstas
        assert Dokumentas.query.count() == 0


class TestAtaskaitos:
    def test_ataskaitos_duomenys(self, admin, mokytojas, vaikas):
        _posedis_su_svarstymu(vaikas, mokytojas, admin)
        _pazyma(vaikas)
        s = ataskaitos_duomenys(date(2026, 12, 1), date(2026, 12, 31))
        assert s["klases"] == [("5A", 1)] and s["mokiniu_is_viso"] == 1
        assert s["vgk_posedziai"] == 1 and s["vgk_aktyvus"] == 1
        assert s["priemones_is_viso"] == 1 and s["priemones_ivykdyta"] == 0

    def test_netinkamas_laikotarpis(self):
        with pytest.raises(PrasymoKlaida):
            parengti_ataskaita(date(2026, 12, 31), date(2026, 12, 1))

    @pytest.mark.parametrize("siandien, laukiama", [
        (date(2026, 12, 1), (date(2026, 11, 1), date(2026, 11, 30))),
        (date(2027, 1, 1), (date(2026, 12, 1), date(2026, 12, 31))),
        (date(2028, 3, 1), (date(2028, 2, 1), date(2028, 2, 29))),
    ])
    def test_ankstesnis_menuo(self, siandien, laukiama):
        assert ankstesnis_menuo(siandien) == laukiama

    def test_menesio_suvestine_viena_per_diena_ir_pranesama(self, numatytosios_taisykles, admin):
        numatytosios_taisykles["menesio_suvestine"].aktyvi = True
        db.session.commit()
        dokumentas = sukurti_menesio_suvestine(date(2026, 12, 1))
        assert dokumentas.tipas == "AT" and dokumentas.sukure_id is None
        assert laikotarpio_pavadinimas(date(2026, 11, 1)) == "2026 m. lapkritis"
        laiskas = EilesIrasas.query.filter_by(gavejo_id=admin.id).one()
        assert laiskas.tema == "Mėnesio suvestinė: 2026 m. lapkritis"
        assert sukurti_menesio_suvestine(date(2026, 12, 1)) is None


class TestPuslapiai:
    def test_tevo_pazymu_puslapis_ir_uzsakymas(self, prisijunges_tevas, vaikas):
        html = prisijunges_tevas.get("/dokumentai/mano-pazymos").get_data(as_text=True)
        assert "Užsakykite pažymą apie vaiko mokymąsi mokykloje" in html
        assert "Pateikti „Sodrai“" in html and "Užsakyti pažymą" in html
        prisijunges_tevas.post("/dokumentai/mano-pazymos", data={"mokinio_id": vaikas.id, "paskirtis": "Darbdaviui"})
        assert PazymosPrasymas.query.one().paskirtis == "Darbdaviui"

    def test_tevas_negali_uzsakyti_svetimam_vaikui(self, prisijunges_tevas, klase):
        svetimas = Mokinys(vardas="Svetimas", pavarde="Vaikas", klases_id=klase.id)
        db.session.add(svetimas)
        db.session.commit()
        html = prisijunges_tevas.post("/dokumentai/mano-pazymos", follow_redirects=True,
                                      data={"mokinio_id": svetimas.id, "paskirtis": "Darbdaviui"}).get_data(as_text=True)
        assert "tik apie savo vaiką" in html
        assert PazymosPrasymas.query.count() == 0

    def test_administratorius_patvirtina_ir_tevas_atsisiuncia(self, client, admin, tevas, vaikas):
        prasymas = pateikti_prasyma(tevas, vaikas, "Darbdaviui")
        client.post("/login", data={"email": admin.email, "slaptazodis": "admin123"})
        assert "Patvirtinti ir parengti pažymą" in client.get("/dokumentai/prasymai").get_data(as_text=True)
        client.post(f"/dokumentai/prasymai/{prasymas.id}/patvirtinti")
        dokumentas = Dokumentas.query.one()
        client.get("/logout")

        client.post("/login", data={"email": tevas.email, "slaptazodis": "tevas123"})
        atsakymas = client.get(f"/dokumentai/{dokumentas.id}/atsisiusti")
        assert atsakymas.status_code == 200
        assert atsakymas.mimetype == "application/pdf"
        assert atsakymas.data[:5] == b"%PDF-"

    def test_svetimas_dokumentas_grazina_404(self, client, mokytojas, vaikas):
        dokumentas = _pazyma(vaikas)
        client.post("/login", data={"email": mokytojas.email, "slaptazodis": "mokytojas123"})
        assert client.get(f"/dokumentai/{dokumentas.id}/atsisiusti").status_code == 404

    def test_registras_paieska_ir_vientisumas(self, prisijunges_admin, vaikas, klase):
        kitas = Mokinys(vardas="Gabija", pavarde="Kitaitė", klases_id=klase.id)
        db.session.add(kitas)
        db.session.commit()
        pirmas, antras = _pazyma(vaikas), _pazyma(kitas)
        html = prisijunges_admin.get("/dokumentai/?mokinys=Kitait").get_data(as_text=True)
        assert antras.numeris in html and pirmas.numeris not in html
        html = prisijunges_admin.get(f"/dokumentai/?numeris={pirmas.numeris}").get_data(as_text=True)
        assert pirmas.numeris in html and antras.numeris not in html
        html = prisijunges_admin.post(f"/dokumentai/{pirmas.id}/tikrinti", follow_redirects=True).get_data(as_text=True)
        assert "kontrolinė suma sutampa" in html

    def test_ataskaita_uz_laikotarpi(self, prisijunges_admin):
        prisijunges_admin.post("/dokumentai/ataskaita", data={"nuo": "2026-11-01", "iki": "2026-11-30"})
        assert Dokumentas.query.one().tipas == "AT"

    def test_mokytojui_registras_neprieinamas(self, client, mokytojas):
        client.post("/login", data={"email": mokytojas.email, "slaptazodis": "mokytojas123"})
        assert client.get("/dokumentai/").status_code == 302

    def test_meniu_punktai(self, prisijunges_tevas):
        assert "Pažymos" in prisijunges_tevas.get("/tevams/").get_data(as_text=True)
