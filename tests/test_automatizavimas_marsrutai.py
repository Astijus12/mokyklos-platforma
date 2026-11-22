"""Automatizavimo modulio puslapių ir esamų modulių įvykių testai.

Prieiga (tik administratorius), taisyklių sąrašas pagal maketą, jungiklis,
taisyklių ir šablonų formos, siuntimo žurnalas (FR-A09), naudotojo nustatymai
(FR-A07) ir įvykių skelbimas skelbimų bei kalendoriaus moduliuose.
"""
from datetime import date

import pytest

from models import (
    AutomatizavimoTaisykle,
    EilesIrasas,
    PranesimoSablonas,
    PranesimuNustatymas,
    Renginys,
    VeiklosZurnalas,
    db,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def prisijunges_mokytojas(client, mokytojas):
    client.post("/login", data={"email": mokytojas.email, "slaptazodis": "mokytojas123"})
    return client


def _html(atsakymas):
    return atsakymas.get_data(as_text=True)


class TestPrieiga:
    PUSLAPIAI = ["/automatizavimas/", "/automatizavimas/sablonai", "/automatizavimas/zurnalas",
                 "/automatizavimas/taisykles/nauja", "/automatizavimas/sablonai/naujas"]

    # Kaip ir kituose administravimo puslapiuose (routes/auth.py admin_required),
    # ne administratorius nukreipiamas į pradžios puslapį su pranešimu.
    @pytest.mark.parametrize("kelias", PUSLAPIAI)
    def test_mokytojui_draudziama(self, prisijunges_mokytojas, kelias):
        atsakymas = prisijunges_mokytojas.get(kelias)
        assert atsakymas.status_code == 302
        assert atsakymas.headers["Location"].endswith("/dashboard")

    @pytest.mark.parametrize("kelias", PUSLAPIAI)
    def test_tevui_draudziama(self, prisijunges_tevas, kelias):
        atsakymas = prisijunges_tevas.get(kelias)
        assert atsakymas.status_code == 302
        assert "/automatizavimas" not in atsakymas.headers["Location"]

    def test_mokytojas_negali_perjungti_taisykles(self, prisijunges_mokytojas, numatytosios_taisykles):
        taisykle = numatytosios_taisykles["skelbimas_paskelbtas"]
        prisijunges_mokytojas.post(f"/automatizavimas/taisykles/{taisykle.id}/perjungti")
        assert db.session.get(AutomatizavimoTaisykle, taisykle.id).aktyvi is True

    def test_neprisijungusiam_nukreipiama_prisijungti(self, client):
        atsakymas = client.get("/automatizavimas/")
        assert atsakymas.status_code == 302
        assert "/login" in atsakymas.headers["Location"]


class TestTaisykliuPuslapis:
    def test_sarasas_kaip_makete(self, prisijunges_admin, numatytosios_taisykles):
        html = _html(prisijunges_admin.get("/automatizavimas/"))
        assert "Automatizavimo taisyklės" in html
        assert "17 taisyklių" in html and "13 aktyvių" in html
        assert "Naujas skelbimas tėvams" in html
        assert "1 diena iki renginio" in html
        assert "2 darbo dienos iki termino" in html
        assert "Kiekvieno mėnesio 1 d." in html
        assert "Nariai, tėvai" in html
        assert "Siuntimo žurnalas (paskutinės 24 val.)" in html
        assert html.count('role="switch"') == 17

    def test_meniu_grupe_procesai(self, prisijunges_admin):
        html = _html(prisijunges_admin.get("/dashboard"))
        assert "Procesai" in html and "Automatizavimas" in html

    def test_jungiklis_isjungia_ir_ijungia(self, prisijunges_admin, numatytosios_taisykles):
        taisykle = numatytosios_taisykles["skelbimas_paskelbtas"]
        atsakymas = prisijunges_admin.post(f"/automatizavimas/taisykles/{taisykle.id}/perjungti")
        assert atsakymas.status_code == 302
        assert db.session.get(AutomatizavimoTaisykle, taisykle.id).aktyvi is False
        assert VeiklosZurnalas.query.filter_by(veiksmas="taisykle_isjungta").count() == 1

        atsakymas = prisijunges_admin.post(f"/automatizavimas/taisykles/{taisykle.id}/perjungti",
                                           headers={"X-Requested-With": "fetch"})
        assert atsakymas.get_json() == {"aktyvi": True}

    def _forma(self, numatytosios_taisykles, **pakeitimai):
        forma = {
            "pavadinimas": "Renginio priminimas darbuotojams",
            "ivykio_tipas": "renginys_artejantis",
            "gavejai": "darbuotojai",
            "kanalai": ["el_pastas", "sistema"],
            "sablono_id": numatytosios_taisykles["renginys_artejantis"].sablono_id,
            "poslinkis_d": "3",
            "salyga": "",
            "aktyvi": "on",
        }
        forma.update(pakeitimai)
        return forma

    def test_nauja_taisykle(self, prisijunges_admin, numatytosios_taisykles):
        atsakymas = prisijunges_admin.post("/automatizavimas/taisykles/nauja",
                                           data=self._forma(numatytosios_taisykles))
        assert atsakymas.status_code == 302
        nauja = AutomatizavimoTaisykle.query.filter_by(pavadinimas="Renginio priminimas darbuotojams").one()
        assert (nauja.kanalas, nauja.poslinkis_d, nauja.aktyvi) == ("el_pastas,sistema", 3, True)

    @pytest.mark.parametrize("pakeitimai, klaida", [
        ({"gavejai": "atsakingas"}, "gavėjų grupė šiam įvykiui netinka"),
        ({"salyga": "{neteisingas json"}, "teisingas JSON"),
        ({"salyga": '{"_slapta": 1}'}, "Netinkamas lauko pavadinimas"),
        ({"kanalai": []}, "bent vieną kanalą"),
        ({"poslinkis_d": "99"}, "Poslinkis turi būti"),
        ({"pavadinimas": ""}, "pavadinimą"),
    ])
    def test_netinkama_taisykle_neissaugoma(self, prisijunges_admin, numatytosios_taisykles, pakeitimai, klaida):
        pries = AutomatizavimoTaisykle.query.count()
        html = _html(prisijunges_admin.post("/automatizavimas/taisykles/nauja",
                                            data=self._forma(numatytosios_taisykles, **pakeitimai)))
        assert klaida in html
        assert AutomatizavimoTaisykle.query.count() == pries

    def test_ne_priminimui_poslinkis_nuliuojamas(self, prisijunges_admin, numatytosios_taisykles):
        forma = self._forma(numatytosios_taisykles, ivykio_tipas="skelbimas_paskelbtas", gavejai="tevai",
                            salyga='{"matomas_tevams": true}')
        prisijunges_admin.post("/automatizavimas/taisykles/nauja", data=forma)
        nauja = AutomatizavimoTaisykle.query.filter_by(pavadinimas=forma["pavadinimas"]).one()
        assert nauja.poslinkis_d == 0
        assert nauja.salyga == {"matomas_tevams": True}

    def test_redagavimas_ir_salinimas(self, prisijunges_admin, numatytosios_taisykles):
        taisykle = numatytosios_taisykles["renginys_artejantis"]
        assert prisijunges_admin.get(f"/automatizavimas/taisykles/{taisykle.id}/redaguoti").status_code == 200
        prisijunges_admin.post(f"/automatizavimas/taisykles/{taisykle.id}/redaguoti",
                               data=self._forma(numatytosios_taisykles, gavejai="tevai", poslinkis_d="2"))
        assert db.session.get(AutomatizavimoTaisykle, taisykle.id).poslinkis_d == 2

        prisijunges_admin.post(f"/automatizavimas/taisykles/{taisykle.id}/salinti")
        assert db.session.get(AutomatizavimoTaisykle, taisykle.id) is None


class TestSablonuPuslapiai:
    def test_sarasas(self, prisijunges_admin, numatytosios_taisykles):
        html = _html(prisijunges_admin.get("/automatizavimas/sablonai"))
        assert "Komisijos posėdžio kvietimas" in html and "vgk_kvietimas" in html

    def test_naujas_sablonas(self, prisijunges_admin):
        prisijunges_admin.post("/automatizavimas/sablonai/naujas", data={
            "kodas": "susirinkimas", "pavadinimas": "Tėvų susirinkimas",
            "tema": "Susirinkimas {{ renginys.data }}", "tekstas": "Sveiki, {{ gavejas.vardas }}!",
        })
        assert PranesimoSablonas.query.filter_by(kodas="susirinkimas").count() == 1

    @pytest.mark.parametrize("pakeitimai, klaida", [
        ({"tekstas": "{{ ''.__class__.__mro__ }}"}, "Šablono klaida"),
        ({"tekstas": "{{ nezinomas_kintamasis }}"}, "Šablono klaida"),
        ({"kodas": "Netinkamas Kodas"}, "Kodas"),
        ({"tema": ""}, "privalomi"),
    ])
    def test_netinkamas_sablonas_neissaugomas(self, prisijunges_admin, pakeitimai, klaida):
        forma = {"kodas": "bandymas", "pavadinimas": "Bandymas", "tema": "Tema", "tekstas": "Tekstas"}
        forma.update(pakeitimai)
        html = _html(prisijunges_admin.post("/automatizavimas/sablonai/naujas", data=forma))
        assert klaida in html
        assert PranesimoSablonas.query.count() == 0

    def test_perziura(self, prisijunges_admin):
        geras = prisijunges_admin.post("/automatizavimas/sablonai/perziura",
                                       data={"tema": "{{ renginys.pavadinimas }}", "tekstas": "{{ posedis.data }}"})
        assert geras.get_json() == {"ok": True, "tema": "Kalėdinis koncertas", "tekstas": "2026-12-08"}
        blogas = prisijunges_admin.post("/automatizavimas/sablonai/perziura",
                                        data={"tema": "{{ nera.tokio }}", "tekstas": "x"})
        assert blogas.get_json()["ok"] is False

    def test_naudojamo_sablono_pasalinti_negalima(self, prisijunges_admin, numatytosios_taisykles):
        sablonas = numatytosios_taisykles["skelbimas_paskelbtas"].sablonas
        html = _html(prisijunges_admin.post(f"/automatizavimas/sablonai/{sablonas.id}/salinti",
                                            follow_redirects=True))
        assert "jį naudoja taisyklės" in html
        assert db.session.get(PranesimoSablonas, sablonas.id) is not None


class TestSiuntimoZurnalas:
    def _irasas(self, gavejas, raktas, busena=EilesIrasas.LAUKIA, **laukai):
        irasas = EilesIrasas(gavejo_id=gavejas.id, kanalas="el_pastas", tema=f"Tema {raktas}",
                             tekstas="t", unikalus_raktas=raktas, busena=busena, **laukai)
        db.session.add(irasas)
        db.session.commit()
        return irasas

    def test_irasai_ir_filtras(self, prisijunges_admin, tevas):
        self._irasas(tevas, "issiustas", EilesIrasas.ISSIUSTAS)
        self._irasas(tevas, "nepavykes", EilesIrasas.NEPAVYKO, bandymai=4, klaida="SMTP klaida")
        visi = _html(prisijunges_admin.get("/automatizavimas/zurnalas"))
        assert "Tema issiustas" in visi and "Tema nepavykes" in visi and "SMTP klaida" in visi
        filtruoti = _html(prisijunges_admin.get("/automatizavimas/zurnalas?busena=nepavyko"))
        assert "Tema nepavykes" in filtruoti and "Tema issiustas" not in filtruoti
        paieska = _html(prisijunges_admin.get("/automatizavimas/zurnalas?paieska=tevas@test.lt"))
        assert "Tema issiustas" in paieska

    def test_pakartoti_nepavykusi(self, prisijunges_admin, tevas):
        irasas = self._irasas(tevas, "a", EilesIrasas.NEPAVYKO, bandymai=4)
        prisijunges_admin.post(f"/automatizavimas/zurnalas/{irasas.id}/pakartoti")
        db.session.refresh(irasas)
        assert (irasas.busena, irasas.bandymai) == (EilesIrasas.LAUKIA, 0)


class TestNaudotojoNustatymai:
    def test_tevas_mato_tik_jam_skirtus_ivykius(self, prisijunges_tevas):
        html = _html(prisijunges_tevas.get("/automatizavimas/mano-nustatymai"))
        assert "Paskelbtas skelbimas" in html
        assert "Įvykdytas pažymos prašymas" in html
        assert "Suplanuotas komisijos posėdis" in html and "Privalomas pranešimas" in html
        assert "Baigtas duomenų importas" not in html

    def test_atsisakymas_issaugomas_o_privalomi_neliečiami(self, prisijunges_tevas, tevas):
        prisijunges_tevas.post("/automatizavimas/mano-nustatymai",
                               data={"el_pastas_renginys_artejantis": "on"})
        nustatymai = {n.ivykio_tipas: n.el_pastas for n in
                      PranesimuNustatymas.query.filter_by(vartotojo_id=tevas.id)}
        assert nustatymai["skelbimas_paskelbtas"] is False
        assert nustatymai["renginys_artejantis"] is True
        assert "vgk_posedis_suplanuotas" not in nustatymai

    def test_mokytojas_ne_vgk_narys_nemato_vgk_posedziu(self, prisijunges_mokytojas):
        html = _html(prisijunges_mokytojas.get("/automatizavimas/mano-nustatymai"))
        assert "Artėja priemonės terminas" in html
        assert "Suplanuotas komisijos posėdis" not in html


class TestIvykiaiEsamuoseModuliuose:
    def test_naujas_skelbimas_sukuria_pranesimus_tevams(self, prisijunges_admin, numatytosios_taisykles, tevas):
        prisijunges_admin.post("/skelbimai/naujas", data={
            "pavadinimas": "Kalėdinis koncertas", "turinys": "Kviečiame!", "matomas_tevams": "on",
        })
        irasas = EilesIrasas.query.one()
        assert irasas.gavejo_id == tevas.id
        assert irasas.tema == "Naujas skelbimas: Kalėdinis koncertas"

    def test_renginio_sukurimas_ir_pakeitimas(self, prisijunges_admin, numatytosios_taisykles, tevas):
        for tipas in ("renginys_sukurtas", "renginys_pakeistas"):
            numatytosios_taisykles[tipas].aktyvi = True
        db.session.commit()
        forma = {"pavadinimas": "Tėvų susirinkimas", "pradzios_data": "2026-12-10", "matomas_tevams": "on"}
        prisijunges_admin.post("/kalendorius/naujas", data=forma)
        renginys = Renginys.query.one()
        assert EilesIrasas.query.count() == 1

        forma["pradzios_data"] = "2026-12-11"
        atsakymas = prisijunges_admin.post(f"/kalendorius/{renginys.id}/redaguoti", data=forma)
        assert atsakymas.status_code == 302
        assert db.session.get(Renginys, renginys.id).pradzios_data == date(2026, 12, 11)
        temos = [i.tema for i in EilesIrasas.query.order_by(EilesIrasas.id)]
        assert temos[1] == "Pasikeitė renginio informacija: Tėvų susirinkimas"

    def test_renginio_salinimas_atsaukia_neissiustus(self, prisijunges_admin, admin, tevas):
        renginys = Renginys(pavadinimas="Ekskursija", pradzios_data=date(2026, 12, 15), vartotojo_id=admin.id)
        db.session.add(renginys)
        db.session.commit()
        irasas = EilesIrasas(gavejo_id=tevas.id, kanalas="el_pastas", tema="t", tekstas="t",
                             unikalus_raktas=f"renginys-{renginys.id}/renginys_artejantis/t1/g{tevas.id}/el_pastas")
        db.session.add(irasas)
        db.session.commit()
        prisijunges_admin.post(f"/kalendorius/{renginys.id}/salinti")
        db.session.refresh(irasas)
        assert irasas.busena == EilesIrasas.ATSAUKTAS

    def test_svetimo_renginio_redaguoti_negalima(self, prisijunges_mokytojas, admin):
        renginys = Renginys(pavadinimas="Administracijos", pradzios_data=date(2026, 12, 15), vartotojo_id=admin.id)
        db.session.add(renginys)
        db.session.commit()
        assert prisijunges_mokytojas.get(f"/kalendorius/{renginys.id}/redaguoti").status_code == 403

    def test_pranesimu_sarase_tekstas_apsaugotas(self, prisijunges_admin):
        html = _html(prisijunges_admin.get("/dashboard"))
        assert "apsaugotiHtml(p.pavadinimas)" in html
        assert "Naujų pranešimų nėra" in html
