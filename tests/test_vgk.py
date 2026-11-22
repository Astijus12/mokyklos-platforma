"""VGK modulio testai (FR-V01–FR-V11, NFR-06, NFR-09, NFR-10).

Kreipimasis, posėdžio planavimas su 5 darbo dienų patikra, kvietimai ir jų
atšaukimas, nutarimai ir priemonės, protokolas, atvejo užbaigimas, vėluojančios
priemonės, prieigos teisės ir veiklos žurnalas.
"""
from datetime import date, time, timedelta

import pytest

from models import (
    Dokumentas,
    EilesIrasas,
    User,
    VeiklosZurnalas,
    VgkAtvejis,
    VgkPosedis,
    VgkPriemone,
    db,
)
from services.kalendorius import prideti_darbo_dienas
from services.vgk import (
    VgkKlaida,
    atnaujinti_atveji,
    atsaukti_posedi,
    dalyviu_grupes,
    gali_uzbaigti,
    irasyti_posedzio_duomenis,
    issaugoti_posedi,
    pateikti_kreipimasi,
    pazymeti_ivykdyta,
    pazymeti_veluojancias,
    prideti_priemone,
    uzbaigti_atveji,
    uzbaigti_posedi,
)

pytestmark = pytest.mark.integration

LAIKAS = time(14, 0)


@pytest.fixture(autouse=True)
def dokumentu_katalogas(app, tmp_path):
    senas = app.config["DOKUMENTU_KATALOGAS"]
    app.config["DOKUMENTU_KATALOGAS"] = str(tmp_path)
    yield
    app.config["DOKUMENTU_KATALOGAS"] = senas


@pytest.fixture
def pirmininke(db_session):
    naudotojas = User(vardas="Ona", pavarde="Kazlauskienė", email="ona@test.lt", role="mokytojas",
                      vgk_pareigos="pirmininkas")
    naudotojas.nustatyti_slaptazodi("slaptas123")
    db_session.add(naudotojas)
    db_session.commit()
    return naudotojas


@pytest.fixture
def atvejis(db_session, vaikas, mokytojas):
    a = VgkAtvejis(mokinio_id=vaikas.id, pateike_id=mokytojas.id, priezastis="Mokymosi sunkumai matematikoje")
    db_session.add(a)
    db_session.commit()
    return a


def _uz(darbo_dienu):
    return prideti_darbo_dienas(date.today(), darbo_dienu)


def _patvirtintas_posedis(atvejis, **papildomai):
    return issaugoti_posedi(None, _uz(6), LAIKAS, "Mokytojų kambarys", [atvejis],
                            {"nariai", f"tevai_{atvejis.id}"}, patvirtinti=True, **papildomai)


class TestKreipimasis:
    def test_uzregistruojamas_ir_pranesama_pirmininkui(self, numatytosios_taisykles, mokytojas, vaikas,
                                                       pirmininke):
        a = pateikti_kreipimasi(mokytojas, vaikas, "Dažnai praleidžia pamokas, prašome įvertinti")
        assert a.busena == VgkAtvejis.UZREGISTRUOTAS and a.pateike_id == mokytojas.id
        irasai = EilesIrasas.query.filter_by(gavejo_id=pirmininke.id).all()
        assert {i.kanalas for i in irasai} == {"el_pastas", "sistema"}
        laiskas = next(i for i in irasai if i.kanalas == "el_pastas")
        assert a.numeris in laiskas.tekstas
        assert vaikas.pavarde not in laiskas.tekstas  # NFR-10: be mokinio vardo ir priežasties
        assert "pamokas" not in laiskas.tekstas

    @pytest.mark.parametrize("priezastis", ["", "trumpa"])
    def test_be_priezasties_negalima(self, mokytojas, vaikas, priezastis):
        with pytest.raises(VgkKlaida):
            pateikti_kreipimasi(mokytojas, vaikas, priezastis)

    def test_be_mokinio_negalima(self, mokytojas):
        with pytest.raises(VgkKlaida):
            pateikti_kreipimasi(mokytojas, None, "Pakankamai ilga priežastis")


class TestPosedzioPlanavimas:
    def test_juodrastis_kvietimu_nesiuncia(self, numatytosios_taisykles, atvejis, pirmininke, tevas):
        posedis = issaugoti_posedi(None, _uz(2), LAIKAS, "Kabinetas 12", [atvejis], {"nariai"},
                                   kviestiniai="Rasa Psichologė\n\n")
        assert posedis.busena == VgkPosedis.JUODRASTIS
        assert atvejis.busena == VgkAtvejis.UZREGISTRUOTAS
        assert EilesIrasas.query.count() == 0
        assert {(d.vardas_pavarde, d.vaidmuo) for d in posedis.dalyviai} == {
            (pirmininke.pilnas_vardas, "pirmininkas"), ("Rasa Psichologė", "kviestinis")}

    def test_patvirtinus_issiunciami_kvietimai_be_esmes(self, numatytosios_taisykles, atvejis, pirmininke,
                                                         tevas, vaikas):
        posedis = _patvirtintas_posedis(atvejis)
        assert posedis.busena == VgkPosedis.SUPLANUOTAS
        assert atvejis.busena == VgkAtvejis.SVARSTOMAS
        gavejai = {i.gavejo_id for i in EilesIrasas.query}
        assert gavejai == {pirmininke.id, tevas.id}
        tevo_laiskas = EilesIrasas.query.filter_by(gavejo_id=tevas.id, kanalas="el_pastas").one()
        assert posedis.vieta in tevo_laiskas.tekstas
        assert vaikas.pavarde not in tevo_laiskas.tekstas and "matematikoje" not in tevo_laiskas.tekstas
        assert "/tevams/" in tevo_laiskas.tekstas  # tėvas gauna nuorodą į savo portalą

    def test_mazai_darbo_dienu_be_skubos_priezasties_negalima(self, atvejis):
        with pytest.raises(VgkKlaida, match="mažiau nei 5 darbo dienos"):
            issaugoti_posedi(None, _uz(3), LAIKAS, "Kabinetas", [atvejis], {"nariai"}, patvirtinti=True)

    def test_su_skubos_priezastimi_galima(self, atvejis):
        posedis = issaugoti_posedi(None, _uz(3), LAIKAS, "Kabinetas", [atvejis], {"nariai"},
                                   skubos_priezastis="Saugumo grėsmė", patvirtinti=True)
        assert posedis.busena == VgkPosedis.SUPLANUOTAS
        assert posedis.skubos_priezastis == "Saugumo grėsmė"

    @pytest.mark.parametrize("pakeitimai, klaida", [
        ({"data": date.today() - timedelta(days=1)}, "praėjusi"),
        ({"vieta": " "}, "datą, laiką ir vietą"),
        ({"atvejai": []}, "bent vieną atvejį"),
    ])
    def test_netinkami_duomenys(self, atvejis, pakeitimai, klaida):
        parametrai = {"data": _uz(6), "laikas": LAIKAS, "vieta": "Kabinetas", "atvejai": [atvejis]}
        parametrai.update(pakeitimai)
        with pytest.raises(VgkKlaida, match=klaida):
            issaugoti_posedi(None, parametrai["data"], parametrai["laikas"], parametrai["vieta"],
                             parametrai["atvejai"], {"nariai"}, patvirtinti=True)

    def test_uzbaigto_atvejo_itraukti_negalima(self, atvejis):
        atvejis.busena = VgkAtvejis.UZBAIGTAS
        db.session.commit()
        with pytest.raises(VgkKlaida, match="Užbaigto"):
            issaugoti_posedi(None, _uz(6), LAIKAS, "Kabinetas", [atvejis], set())

    def test_patvirtinto_posedzio_redaguoti_negalima(self, atvejis):
        posedis = _patvirtintas_posedis(atvejis)
        with pytest.raises(VgkKlaida, match="juodraštį"):
            issaugoti_posedi(posedis, _uz(7), LAIKAS, "Kitur", [atvejis], set())

    def test_dalyviu_grupes(self, atvejis, pirmininke, tevas, mokytojas):
        grupes = {kodas: nariai for kodas, _, nariai in dalyviu_grupes([atvejis])}
        assert [n for n, _ in grupes["nariai"]] == [pirmininke]
        assert [n for n, _ in grupes[f"tevai_{atvejis.id}"]] == [tevas]
        assert [n for n, _ in grupes["vadovai"]] == [mokytojas]

    def test_atsaukus_neissiusti_kvietimai_atsaukiami(self, numatytosios_taisykles, atvejis, pirmininke, tevas):
        posedis = _patvirtintas_posedis(atvejis)
        kvietimai = EilesIrasas.query.count()
        atsaukti_posedi(posedis)
        assert posedis.busena == VgkPosedis.ATSAUKTAS
        assert atvejis.busena == VgkAtvejis.UZREGISTRUOTAS
        senieji = EilesIrasas.query.order_by(EilesIrasas.id).limit(kvietimai).all()
        assert {i.busena for i in senieji} == {EilesIrasas.ATSAUKTAS}
        atsaukimai = EilesIrasas.query.filter(EilesIrasas.unikalus_raktas.contains("vgk_posedis_atsauktas"))
        assert atsaukimai.count() == kvietimai  # apie atšaukimą pranešama tiems patiems dalyviams
        with pytest.raises(VgkKlaida):
            atsaukti_posedi(posedis)


class TestPosedzioEigaIrPriemones:
    def test_nutarimai_priemones_ir_protokolas(self, atvejis, pirmininke, mokytojas):
        posedis = _patvirtintas_posedis(atvejis)
        dalyvis = posedis.dalyviai[0]
        svarstymas = posedis.svarstymai[0]
        with pytest.raises(VgkKlaida, match="pažymėkite posėdžio dalyvius"):
            uzbaigti_posedi(posedis, pirmininke)

        irasyti_posedzio_duomenis(posedis, {dalyvis.id}, {dalyvis.id}, {svarstymas.id: "Skirti konsultacijas"})
        prideti_priemone(svarstymas, "Konsultacijos", mokytojas, _uz(10))
        assert atvejis.busena == VgkAtvejis.TAIKOMOS_PRIEMONES

        protokolas = uzbaigti_posedi(posedis, pirmininke)
        assert posedis.busena == VgkPosedis.IVYKES
        assert protokolas.tipas == "PR" and posedis.protokolo_id == protokolas.id
        assert Dokumentas.query.count() == 1

    def test_priemones_be_duomenu_negalima(self, atvejis, mokytojas):
        svarstymas = _patvirtintas_posedis(atvejis).svarstymai[0]
        with pytest.raises(VgkKlaida):
            prideti_priemone(svarstymas, "", mokytojas, _uz(5))

    def test_uzbaigimas_tik_ivykdzius_priemones_ir_atnaujinimas(self, atvejis, mokytojas, pirmininke, admin):
        posedis = _patvirtintas_posedis(atvejis)
        svarstymas = posedis.svarstymai[0]
        irasyti_posedzio_duomenis(posedis, set(), set(), {svarstymas.id: "Stebėti"})
        priemone = prideti_priemone(svarstymas, "Konsultacijos", mokytojas, _uz(5))
        assert gali_uzbaigti(atvejis) is False
        with pytest.raises(VgkKlaida):
            uzbaigti_atveji(atvejis)

        kitas = User(vardas="Kitas", pavarde="Mokytojas", email="kitas@test.lt", role="mokytojas")
        kitas.nustatyti_slaptazodi("x")
        db.session.add(kitas)
        db.session.commit()
        with pytest.raises(VgkKlaida):
            pazymeti_ivykdyta(priemone, kitas, "")
        pazymeti_ivykdyta(priemone, mokytojas, "Įvyko 4 konsultacijos")
        assert priemone.busena == VgkPriemone.IVYKDYTA and priemone.rezultatas == "Įvyko 4 konsultacijos"

        uzbaigti_atveji(atvejis)
        assert atvejis.busena == VgkAtvejis.UZBAIGTAS and atvejis.uzbaigta is not None
        atnaujinti_atveji(atvejis)
        assert atvejis.busena == VgkAtvejis.UZREGISTRUOTAS and atvejis.uzbaigta is None

    def test_veluojancios_priemones_pirmininkui(self, numatytosios_taisykles, atvejis, mokytojas, pirmininke):
        svarstymas = _patvirtintas_posedis(atvejis).svarstymai[0]
        priemone = prideti_priemone(svarstymas, "Pokalbis su tėvais", mokytojas, date.today() + timedelta(days=1))
        assert pazymeti_veluojancias(date.today() + timedelta(days=3)) == 1
        assert priemone.busena == VgkPriemone.VELUOJA
        assert EilesIrasas.query.filter(EilesIrasas.gavejo_id == pirmininke.id,
                                        EilesIrasas.unikalus_raktas.contains("priemone_veluoja")).count() == 1
        assert pazymeti_veluojancias(date.today() + timedelta(days=3)) == 0


class TestPuslapiaiIrTeises:
    def _prisijungti(self, client, naudotojas, slaptazodis):
        client.post("/login", data={"email": naudotojas.email, "slaptazodis": slaptazodis})
        return client

    def test_ne_nariams_404(self, client, mokytojas, atvejis):
        self._prisijungti(client, mokytojas, "mokytojas123")
        for kelias in ("/vgk/", f"/vgk/atvejai/{atvejis.id}", "/vgk/posedziai"):
            assert client.get(kelias).status_code == 404

    def test_tevui_404(self, prisijunges_tevas, atvejis):
        assert prisijunges_tevas.get(f"/vgk/atvejai/{atvejis.id}").status_code == 404

    def test_narys_mato_bet_neplanuoja(self, client, atvejis):
        narys = User(vardas="Narys", pavarde="Komisijos", email="narys@test.lt", role="mokytojas",
                     vgk_pareigos="narys")
        narys.nustatyti_slaptazodi("slaptas123")
        db.session.add(narys)
        db.session.commit()
        self._prisijungti(client, narys, "slaptas123")
        assert client.get(f"/vgk/atvejai/{atvejis.id}").status_code == 200
        assert client.get("/vgk/posedziai/naujas").status_code == 403

    def test_atvejo_kortele_kaip_makete_ir_zurnalas(self, client, pirmininke, atvejis):
        self._prisijungti(client, pirmininke, "slaptas123")
        html = client.get(f"/vgk/atvejai/{atvejis.id}").get_data(as_text=True)
        for tekstas in (f"Atvejis Nr. {atvejis.numeris}", "Atvejo duomenys", "Svarstymai posėdžiuose",
                        "Priemonės", "Įtraukti į posėdį", "Kreipimosi priežastis"):
            assert tekstas in html
        assert VeiklosZurnalas.query.filter_by(veiksmas="vgk_perziura", objekto_id=atvejis.id).count() == 1

    def test_mokytojo_kreipimasis_ir_busena(self, client, mokytojas, vaikas):
        self._prisijungti(client, mokytojas, "mokytojas123")
        client.post("/vgk/kreipimasis", data={"mokinio_id": vaikas.id,
                                              "priezastis": "Pastebėti adaptacijos sunkumai klasėje"})
        atvejis = VgkAtvejis.query.one()
        html = client.get("/vgk/mano-kreipimaisi").get_data(as_text=True)
        assert atvejis.numeris in html and "Užregistruotas" in html
        assert "adaptacijos sunkumai" not in html  # tik būsena, ne turinys

    def test_posedzio_planavimas_puslapyje(self, client, numatytosios_taisykles, pirmininke, atvejis, tevas):
        self._prisijungti(client, pirmininke, "slaptas123")
        forma = client.get(f"/vgk/posedziai/naujas?atvejai={atvejis.id}").get_data(as_text=True)
        assert "Naujas komisijos posėdis" in forma and "Išsiųsti kvietimus" in forma
        assert client.get(f"/vgk/darbo-dienos?data={_uz(3).isoformat()}").get_json() == \
            {"liko": 3, "pakanka": False, "reikia": 5}

        atsakymas = client.post("/vgk/posedziai/naujas", data={
            "data": _uz(6).isoformat(), "laikas": "14:00", "vieta": "Mokytojų kambarys",
            "atvejai": [str(atvejis.id)], "grupes": ["nariai", f"tevai_{atvejis.id}"], "veiksmas": "patvirtinti",
        })
        posedis = VgkPosedis.query.one()
        assert atsakymas.headers["Location"].endswith(f"/vgk/posedziai/{posedis.id}")
        assert posedis.busena == VgkPosedis.SUPLANUOTAS
        assert EilesIrasas.query.filter_by(gavejo_id=tevas.id).count() == 2

    def test_per_trumpas_terminas_puslapyje(self, client, pirmininke, atvejis):
        self._prisijungti(client, pirmininke, "slaptas123")
        html = client.post("/vgk/posedziai/naujas", follow_redirects=True, data={
            "data": _uz(2).isoformat(), "laikas": "14:00", "vieta": "Kabinetas",
            "atvejai": [str(atvejis.id)], "grupes": ["nariai"], "veiksmas": "patvirtinti",
        }).get_data(as_text=True)
        assert "skubos priežastį" in html
        assert VgkPosedis.query.count() == 0

    def test_posedzio_eiga_puslapyje_ir_protokolo_atsisiuntimas(self, client, pirmininke, atvejis, mokytojas):
        posedis = _patvirtintas_posedis(atvejis)
        dalyvis, svarstymas = posedis.dalyviai[0], posedis.svarstymai[0]
        self._prisijungti(client, pirmininke, "slaptas123")
        assert "Užbaigti ir parengti protokolą" in client.get(f"/vgk/posedziai/{posedis.id}").get_data(as_text=True)
        client.post(f"/vgk/posedziai/{posedis.id}/duomenys", data={
            "dalyvavo": [str(dalyvis.id)], "pasizadejimas": [str(dalyvis.id)],
            f"nutarimas_{svarstymas.id}": "Skirti konsultacijas"})
        client.post(f"/vgk/posedziai/{posedis.id}/svarstymai/{svarstymas.id}/priemones", data={
            "aprasymas": "Konsultacijos", "atsakingo_id": mokytojas.id, "terminas": _uz(10).isoformat()})
        client.post(f"/vgk/posedziai/{posedis.id}/uzbaigti")
        db.session.refresh(posedis)
        assert posedis.busena == VgkPosedis.IVYKES and posedis.protokolas is not None
        assert client.get(f"/dokumentai/{posedis.protokolas.id}/atsisiusti").status_code == 200
        client.get("/logout")

        self._prisijungti(client, mokytojas, "mokytojas123")  # ne komisijos narys
        assert client.get(f"/dokumentai/{posedis.protokolas.id}/atsisiusti").status_code == 404
        html = client.get("/vgk/mano-priemones").get_data(as_text=True)
        assert "Konsultacijos" in html and "Pažymėti įvykdyta" in html
        priemone = VgkPriemone.query.one()
        client.post(f"/vgk/priemones/{priemone.id}/ivykdyta", data={"rezultatas": "Atlikta"})
        assert db.session.get(VgkPriemone, priemone.id).busena == VgkPriemone.IVYKDYTA

    def test_meniu_punktas_darbuotojams(self, client, mokytojas):
        self._prisijungti(client, mokytojas, "mokytojas123")
        html = client.get("/dashboard").get_data(as_text=True)
        assert "Vaiko gerovės komisija" in html and "/vgk/mano-kreipimaisi" in html
