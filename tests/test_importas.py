"""Masinio importo testai (FR-I01–FR-I07, NFR-04, NFR-08).

Eilučių tikrinimas be failų, failų nuskaitymas ir apribojimai, įrašymas viena
transakcija (klaidos atveju neįrašoma nieko), tėvų paskyros su vienkartine
slaptažodžio nuoroda, puslapiai ir 500 eilučių tikrinimo trukmė.
"""
import io
import time

import pytest
from openpyxl import Workbook

from models import EilesIrasas, ImportoEilute, ImportoSesija, Klase, Mokinys, Pranesimas, User, db
from services import importas as importo_modulis
from services.importas import EiluciuTikrintojas, ImportoKlaida, ImportoVykdytojas, ataskaitos_csv
from services.paskyros import naudotojas_pagal_zetona, nustatyti_slaptazodi, slaptazodzio_zetonas

pytestmark = pytest.mark.integration

ANTRASTES = "Vardas;Pavardė;Gimimo data;Klasė;Tėvo (globėjo) vardas, pavardė;Tėvo (globėjo) el. paštas"


def _csv(*eilutes):
    return ("\ufeff" + "\n".join((ANTRASTES,) + eilutes)).encode("utf-8")


def _xlsx(eilutes, antrastes=("Vardas", "Pavardė", "Gimimo data", "Klasė", "Tėvo (globėjo) el. paštas")):
    knyga = Workbook()
    lapas = knyga.active
    lapas.append(list(antrastes))
    for eilute in eilutes:
        lapas.append(list(eilute))
    buferis = io.BytesIO()
    knyga.save(buferis)
    return buferis.getvalue()


def _importuoti(admin, turinys, failas="mokiniai.csv"):
    vykdytojas = ImportoVykdytojas()
    sesija = vykdytojas.nuskaityti(failas, turinys, admin)
    vykdytojas.tikrinti(sesija)
    db.session.commit()
    return vykdytojas, sesija


class TestEiluciuTikrintojas:
    def setup_method(self):
        self.tikrintojas = EiluciuTikrintojas(["5A", "8B"], {("domas", "butkus", "2014-05-22")})

    def test_tinkama_eilute(self):
        assert self.tikrintojas.tikrinti({"vardas": "Ugnė", "pavarde": "Kairytė", "gimimo_data": "2015-03-21",
                                          "klase": "5a", "tevo_el_pastas": "rasa@pastas.lt"}) == []

    @pytest.mark.parametrize("pakeitimas, klaida", [
        ({"klase": "6C"}, "Klasė „6C“ nerasta"),
        ({"gimimo_data": "2015-13-40"}, "Neteisinga gimimo data"),
        ({"gimimo_data": "21.03.2015"}, "Neteisinga gimimo data"),
        ({"tevo_el_pastas": "ugne.kairiene@pastas"}, "Neteisingas el. paštas"),
        ({"vardas": ""}, "Nenurodytas vardas"),
    ])
    def test_klaidos(self, pakeitimas, klaida):
        eilute = {"vardas": "Ugnė", "pavarde": "Kairytė", "gimimo_data": "2015-03-21", "klase": "5A"}
        eilute.update(pakeitimas)
        assert any(k.startswith(klaida) for k in self.tikrintojas.tikrinti(eilute))

    def test_dublikatai_sistemoje_ir_faile(self):
        eilutes = [(2, {"vardas": "Domas", "pavarde": "Butkus", "gimimo_data": "2014-05-22"}),
                   (3, {"vardas": "Ona", "pavarde": "Nauja", "gimimo_data": "2015-01-01"}),
                   (4, {"vardas": "ONA", "pavarde": "nauja", "gimimo_data": "2015-01-01"})]
        assert self.tikrintojas.rasti_dublikatus(eilutes) == {2: "Jau yra sistemoje", 4: "Pasikartoja faile"}


class TestNuskaitymas:
    def test_csv_su_lietuviskomis_raidemis(self, admin, klase):
        _, sesija = _importuoti(admin, _csv("Ugnė;Kairytė;2015-03-21;5A;Rasa Kairienė;rasa@pastas.lt",
                                            "Jonas;Petrauskas;2015-01-01;6C;;"))
        assert sesija.eiluciu_sk == 2 and sesija.tinkamu_sk == 1 and sesija.klaidu_sk == 1
        assert sesija.eilutes[0].duomenys["pavarde"] == "Kairytė"
        assert sesija.eilutes[1].eilutes_nr == 3 and "6C" in sesija.eilutes[1].klaidos

    def test_xlsx_ir_formules_nevykdomos(self, admin, klase):
        _, sesija = _importuoti(admin, _xlsx([("Ugnė", "Kairytė", "2015-03-21", "5A", "=1+1")]), "mokiniai.xlsx")
        assert sesija.eilutes[0].duomenys["tevo_el_pastas"] == ""  # formulės reikšmė neapskaičiuojama
        assert sesija.tinkamu_sk == 1

    @pytest.mark.parametrize("failas, turinys, klaida", [
        ("mokiniai.txt", b"x", "Tinka tik .xlsx arba .csv"),
        ("mokiniai.xlsx", b"ne xlsx turinys", "neatitinka XLSX"),
        ("mokiniai.csv", b"x" * (2 * 1024 * 1024 + 1), "per didelis"),
        ("mokiniai.csv", "Vardas;Pavardė\nOna;Ona".encode("utf-8"), "Trūksta privalomų stulpelių"),
        ("mokiniai.csv", (ANTRASTES + "\n").encode("utf-8"), "nėra duomenų"),
    ], ids=["pletinys", "ne_xlsx", "per_didelis", "truksta_stulpeliu", "be_duomenu"])
    def test_netinkami_failai(self, admin, failas, turinys, klaida):
        with pytest.raises(ImportoKlaida, match=klaida):
            ImportoVykdytojas().nuskaityti(failas, turinys, admin)

    def test_per_daug_eiluciu(self, admin):
        eilutes = [f"Vardas{i};Pavarde;2015-01-01;5A;;" for i in range(1001)]
        with pytest.raises(ImportoKlaida, match="iki 1000"):
            ImportoVykdytojas().nuskaityti("mokiniai.csv", _csv(*eilutes), admin)

    def test_500_eiluciu_tikrinimas_greitas(self, admin, klase):
        """NFR-04: 500 eilučių XLSX failo patikra trunka ne ilgiau kaip 10 s."""
        eilutes = [(f"Vardas{i}", f"Pavarde{i}", "2015-01-01", "5A", f"tevas{i}@pastas.lt") for i in range(500)]
        pradzia = time.perf_counter()
        _, sesija = _importuoti(admin, _xlsx(eilutes), "didelis.xlsx")
        trukme = time.perf_counter() - pradzia
        assert sesija.tinkamu_sk == 500
        assert trukme < 10, f"Tikrinimas truko {trukme:.1f} s"


class TestIrasymas:
    def test_viena_transakcija_su_tevu_paskyromis_ir_kvietimais(self, numatytosios_taisykles, admin, klase,
                                                               tevas):
        vykdytojas, sesija = _importuoti(admin, _csv(
            "Ugnė;Kairytė;2015-03-21;5A;Rasa Kairienė;rasa@pastas.lt",
            "Gabija;Kairytė;2016-04-02;5A;Rasa Kairienė;RASA@pastas.lt",
            f"Rokas;Tėvaitis;2015-09-09;5A;Esamas Tėvas;{tevas.email}",
            "Klaida;Eilutė;netinkama;5A;;"))
        vykdytojas.irasyti(sesija, admin)

        assert sesija.busena == ImportoSesija.IMPORTUOTA
        assert [e.busena for e in sesija.eilutes].count(ImportoEilute.IRASYTA) == 3
        rasa = User.query.filter_by(email="rasa@pastas.lt").one()
        assert rasa.role == "tevas" and rasa.vardas == "Rasa" and rasa.pavarde == "Kairienė"
        assert sorted(v.vardas for v in rasa.vaikai) == ["Gabija", "Ugnė"]
        assert "Rokas" in [v.vardas for v in tevas.vaikai]
        kvietimas = EilesIrasas.query.filter_by(gavejo_id=rasa.id, kanalas="el_pastas").one()
        assert "/slaptazodis/" in kvietimas.tekstas
        assert EilesIrasas.query.filter_by(gavejo_id=tevas.id).count() == 0  # esamam tėvui kvietimo nėra
        assert EilesIrasas.query.filter(EilesIrasas.gavejo_id == admin.id,
                                        EilesIrasas.unikalus_raktas.contains("importas_baigtas")).count() == 1
        with pytest.raises(ImportoKlaida):
            vykdytojas.irasyti(sesija, admin)

    def test_klaidos_atveju_neirasoma_nieko(self, admin, klase, monkeypatch):
        vykdytojas, sesija = _importuoti(admin, _csv("Ugnė;Kairytė;2015-03-21;5A;;",
                                                     "Gabija;Kairytė;2016-04-02;5A;;"))

        def luzta(*args, **kwargs):
            raise RuntimeError("Imituota klaida įrašant")

        monkeypatch.setattr(importo_modulis, "skelbti", luzta)
        with pytest.raises(RuntimeError):
            vykdytojas.irasyti(sesija, admin)
        assert Mokinys.query.filter_by(pavarde="Kairytė").count() == 0
        assert db.session.get(ImportoSesija, sesija.id).busena == ImportoSesija.KLAIDA

    def test_ataskaitos_csv_apsaugo_nuo_formuliu(self, admin, klase):
        _, sesija = _importuoti(admin, _csv("=HYPERLINK(1);Kairytė;2015-03-21;5A;;"))
        assert "'=HYPERLINK(1)" in ataskaitos_csv(sesija)


class TestSlaptazodzioNuoroda:
    def test_vienkartine_nuoroda(self, tevas):
        zetonas = slaptazodzio_zetonas(tevas)
        assert naudotojas_pagal_zetona(zetonas) == tevas
        assert naudotojas_pagal_zetona("netinkamas") is None
        assert nustatyti_slaptazodi(tevas, "trumpas", "trumpas") == "Slaptažodis turi būti bent 8 simbolių."
        assert nustatyti_slaptazodi(tevas, "IlgasSlaptas1", "kitas") == "Slaptažodžiai nesutampa."
        assert nustatyti_slaptazodi(tevas, "IlgasSlaptas1", "IlgasSlaptas1") is None
        assert naudotojas_pagal_zetona(zetonas) is None  # jau panaudota

    def test_nustatymas_puslapyje(self, client, tevas):
        zetonas = slaptazodzio_zetonas(tevas)
        assert "Sukurkite slaptažodį" in client.get(f"/slaptazodis/{zetonas}").get_data(as_text=True)
        client.post(f"/slaptazodis/{zetonas}", data={"slaptazodis": "NaujasSlaptas1", "pakartotas": "NaujasSlaptas1"})
        assert db.session.get(User, tevas.id).patikrinti_slaptazodi("NaujasSlaptas1")
        assert client.get(f"/slaptazodis/{zetonas}").status_code == 302


class TestPuslapiai:
    def test_ikelimas_perziura_patvirtinimas_ataskaita(self, prisijunges_admin, klase):
        atsakymas = prisijunges_admin.post("/importas/", data={
            "failas": (io.BytesIO(_csv("Ugnė;Kairytė;2015-03-21;5A;;", "Jonas;Petrauskas;2015-01-01;6C;;")),
                       "mokiniai.csv")}, content_type="multipart/form-data")
        sesija = ImportoSesija.query.one()
        assert atsakymas.headers["Location"].endswith(f"/importas/{sesija.id}/perziura")
        html = prisijunges_admin.get(f"/importas/{sesija.id}/perziura").get_data(as_text=True)
        for tekstas in ("Importo peržiūra", "Tinkamos eilutės", "Klaidingos eilutės", "Pasikartojančios",
                        "Klasė „6C“ nerasta", "Įrašyti 1 mokinį"):
            assert tekstas in html
        prisijunges_admin.post(f"/importas/{sesija.id}/patvirtinti")
        assert Mokinys.query.filter_by(vardas="Ugnė").count() == 1
        assert "Importo ataskaita" in prisijunges_admin.get(f"/importas/{sesija.id}/ataskaita").get_data(as_text=True)
        csv_atsakymas = prisijunges_admin.get(f"/importas/{sesija.id}/ataskaita.csv")
        assert csv_atsakymas.mimetype == "text/csv" and "Įrašyta" in csv_atsakymas.get_data(as_text=True)

    def test_netinkamas_failas_rodo_klaida(self, prisijunges_admin):
        html = prisijunges_admin.post("/importas/", follow_redirects=True, content_type="multipart/form-data",
                                      data={"failas": (io.BytesIO(b"x"), "mokiniai.txt")}).get_data(as_text=True)
        assert "Tinka tik .xlsx arba .csv" in html

    def test_sablonas_ir_atsaukimas(self, prisijunges_admin, klase, admin):
        sablonas = prisijunges_admin.get("/importas/sablonas.xlsx")
        assert sablonas.data[:2] == b"PK"
        _, sesija = _importuoti(admin, _csv("Ugnė;Kairytė;2015-03-21;5A;;"))
        prisijunges_admin.post(f"/importas/{sesija.id}/atsaukti")
        assert db.session.get(ImportoSesija, sesija.id).busena == ImportoSesija.ATSAUKTA

    def test_mokytojui_neprieinama(self, client, mokytojas):
        client.post("/login", data={"email": mokytojas.email, "slaptazodis": "mokytojas123"})
        assert client.get("/importas/").status_code == 302

    def test_meniu_punktas(self, prisijunges_admin):
        assert "Duomenų importas" in prisijunges_admin.get("/dashboard").get_data(as_text=True)
