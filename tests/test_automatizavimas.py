"""Automatizavimo posistemio (paslaugų sluoksnio) testai.

Tikrinama: darbo dienų skaičiavimas, šablonai saugioje aplinkoje (NFR-07),
taisyklių variklis, įvykių skirstytuvas (FR-A04, FR-A07, NFR-10), pranešimų
eilė su pakartojimais (FR-A05, FR-A08, FR-A09), kanalai, siuntėjas ir priminimai (FR-A06).
"""
import os
import smtplib
from datetime import date, datetime, time, timedelta

import pytest

from models import (
    AutomatizavimoTaisykle,
    EilesIrasas,
    Pranesimas,
    PranesimoSablonas,
    PranesimuNustatymas,
    Renginys,
    Skelbimas,
    User,
    VgkAtvejis,
    VgkDalyvis,
    VgkPosedis,
    VgkPriemone,
    VgkSvarstymas,
    db,
    utc_dabar,
)
from services.eile import MAKS_BANDYMU, PranesimuEile
from services.ivykiai import IvykiuSkirstytuvas, kelias, sukurti_konteksta, IVYKIU_TIPAI, skelbti
from services.kalendorius import (
    ar_darbo_diena,
    darbo_dienos_iki,
    prideti_darbo_dienas,
    sventes,
    velyku_sekmadienis,
)
from services.kanalai import ElPastoKanalas, Kanalas, SiuntimoKlaida, SistemosKanalas
from services.planuokle import Planuokle
from services.priminimai import PriminimuKurejas
from services.sablonai import SablonoKlaida, SablonuApdorotojas
from services.siuntejas import PranesimuSiuntejas
from services.taisykles import TaisykliuVariklis, patikrinti_salyga

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def laisku_katalogas(app, tmp_path):
    """El. laiškai testuose įrašomi į laikiną katalogą."""
    senas = app.config["MAIL_FAILU_KATALOGAS"]
    app.config["MAIL_FAILU_KATALOGAS"] = str(tmp_path / "laiskai")
    yield tmp_path / "laiskai"
    app.config["MAIL_FAILU_KATALOGAS"] = senas


def _naudotojas(vardas, role, email, **papildomai):
    naudotojas = User(vardas=vardas, pavarde="Testas", email=email, role=role, **papildomai)
    naudotojas.nustatyti_slaptazodi("x")
    db.session.add(naudotojas)
    db.session.commit()
    return naudotojas


@pytest.fixture
def antras_tevas(db_session):
    return _naudotojas("Rasa", "tevas", "rasa@test.lt")


def _skelbimas(autorius, matomas_tevams=True):
    s = Skelbimas(pavadinimas="Atvirų durų diena", turinys="Kviečiame į mokyklą.",
                  matomas_tevams=matomas_tevams, vartotojo_id=autorius.id)
    db.session.add(s)
    db.session.flush()
    return s


def _irasas(gavejas, raktas, **laukai):
    laukai.setdefault("kanalas", "el_pastas")
    laukai.setdefault("tema", "Tema")
    laukai.setdefault("tekstas", "Tekstas")
    irasas = EilesIrasas(gavejo_id=gavejas.id, unikalus_raktas=raktas, **laukai)
    db.session.add(irasas)
    db.session.commit()
    return irasas


def _posedis_su_dalyviu(dalyvis, data, busena=VgkPosedis.SUPLANUOTAS):
    posedis = VgkPosedis(data=data, laikas=time(14, 0), vieta="Mokytojų kambarys", busena=busena)
    posedis.dalyviai.append(VgkDalyvis(vartotojo_id=dalyvis.id, vardas_pavarde=dalyvis.pilnas_vardas,
                                       vaidmuo="tevas"))
    db.session.add(posedis)
    db.session.commit()
    return posedis


# --- Darbo dienos -------------------------------------------------------------------

class TestKalendorius:
    def test_velykos_ir_antroji_velyku_diena(self):
        assert velyku_sekmadienis(2026) == date(2026, 4, 5)
        assert velyku_sekmadienis(2027) == date(2027, 3, 28)
        assert date(2026, 4, 6) in sventes(2026)

    @pytest.mark.parametrize("diena, darbo", [
        (date(2026, 11, 30), True),    # pirmadienis
        (date(2026, 11, 28), False),   # šeštadienis
        (date(2026, 12, 24), False),   # Kūčios
        (date(2026, 2, 16), False),    # Vasario 16-oji
        (date(2026, 4, 6), False),     # Velykų antroji diena
    ])
    def test_ar_darbo_diena(self, diena, darbo):
        assert ar_darbo_diena(diena) is darbo

    def test_nuo_pirmadienio_iki_kito_pirmadienio_5_darbo_dienos(self):
        assert darbo_dienos_iki(date(2026, 11, 30), nuo=date(2026, 11, 23)) == 5

    def test_nuo_penktadienio_iki_pirmadienio_1_darbo_diena(self):
        assert darbo_dienos_iki(date(2026, 11, 30), nuo=date(2026, 11, 27)) == 1

    def test_kaledu_atostogos_neskaiciuojamos(self):
        assert darbo_dienos_iki(date(2026, 12, 28), nuo=date(2026, 12, 23)) == 1
        assert prideti_darbo_dienas(date(2026, 12, 23), 1) == date(2026, 12, 28)

    def test_praejusiai_datai_0(self):
        assert darbo_dienos_iki(date(2026, 11, 20), nuo=date(2026, 11, 23)) == 0


# --- Šablonai (FR-A03, NFR-07) --------------------------------------------------------

class TestSablonai:
    def test_formuoja_tema_ir_teksta(self):
        sablonas = PranesimoSablonas(tema="Sveiki,\n {{ gavejas.vardas }}", tekstas="  Tekstas {{ x }}  ")
        tema, tekstas = SablonuApdorotojas().formuoti(sablonas, {"gavejas": {"vardas": "Ona"}, "x": 5})
        assert tema == "Sveiki, Ona"  # tema be eilučių lūžių
        assert tekstas == "Tekstas 5"

    def test_nezinomas_kintamasis_siunciant_tampa_tuscias(self):
        tema, _ = SablonuApdorotojas().formuoti(PranesimoSablonas(tema="A{{ nera }}B", tekstas="t"), {})
        assert tema == "AB"

    def test_perziura_nezinoma_kintamaji_parodo_kaip_klaida(self):
        with pytest.raises(SablonoKlaida):
            SablonuApdorotojas().perziura(PranesimoSablonas(tema="{{ nezinomas.laukas }}", tekstas="t"))

    def test_perziura_su_pavyzdiniais_duomenimis(self):
        tema, tekstas = SablonuApdorotojas().perziura(
            PranesimoSablonas(tema="{{ renginys.pavadinimas }}", tekstas="{{ posedis.vieta }}"))
        assert tema == "Kalėdinis koncertas"
        assert tekstas == "Mokytojų kambarys"

    @pytest.mark.parametrize("kenkejiskas", [
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ gavejas.__class__.__init__.__globals__ }}",
        "{% for i in range(10**9) %}{% endfor %}",
    ])
    def test_sandbox_neleidzia_pasiekti_vidiniu_objektu(self, kenkejiskas):
        """NFR-07: kenkėjiškas šablonas nesuveikia, o grąžina klaidą."""
        with pytest.raises(SablonoKlaida):
            SablonuApdorotojas().formuoti(PranesimoSablonas(tema="t", tekstas=kenkejiskas),
                                          {"gavejas": {"vardas": "Ona"}})

    def test_sintakses_klaida(self):
        klaida = SablonuApdorotojas().patikrinti(PranesimoSablonas(tema="{{ neuzdaryta", tekstas="t"))
        assert klaida

    def test_visi_numatytieji_sablonai_tinkami(self, numatytosios_taisykles):
        apdorotojas = SablonuApdorotojas()
        for sablonas in PranesimoSablonas.query.all():
            assert apdorotojas.patikrinti(sablonas) is None, sablonas.kodas


# --- Taisyklių variklis ---------------------------------------------------------------

class TestTaisykliuVariklis:
    def test_randa_tik_aktyvias_taisykles(self, numatytosios_taisykles):
        variklis = TaisykliuVariklis()
        assert [t.ivykio_tipas for t in variklis.rasti_taisykles("skelbimas_paskelbtas")] == \
            ["skelbimas_paskelbtas"]
        assert variklis.rasti_taisykles("menesio_suvestine") == []  # išjungta

    def test_salyga(self, admin):
        variklis = TaisykliuVariklis()
        skelbimas = _skelbimas(admin, matomas_tevams=False)
        assert variklis.tenkina_salyga(AutomatizavimoTaisykle(salyga=None), skelbimas)
        assert not variklis.tenkina_salyga(AutomatizavimoTaisykle(salyga={"matomas_tevams": True}), skelbimas)
        assert variklis.tenkina_salyga(AutomatizavimoTaisykle(salyga={"kategorija": ["bendra", "renginiai"]}),
                                       skelbimas)
        assert not variklis.tenkina_salyga(AutomatizavimoTaisykle(salyga={"nera_tokio": 1}), skelbimas)
        assert not variklis.tenkina_salyga(AutomatizavimoTaisykle(salyga={"_sa_instance_state": 1}), skelbimas)

    def test_gavejai_be_dublikatu(self, tevas, antras_tevas):
        posedis = _posedis_su_dalyviu(tevas, date(2026, 12, 8))
        posedis.dalyviai.append(VgkDalyvis(vartotojo_id=tevas.id, vardas_pavarde="Dublis", vaidmuo="tevas"))
        posedis.dalyviai.append(VgkDalyvis(vardas_pavarde="Be paskyros", vaidmuo="kviestinis"))
        db.session.commit()
        variklis = TaisykliuVariklis()
        assert variklis.nustatyti_gavejus(AutomatizavimoTaisykle(gavejai="posedzio_dalyviai"), posedis) == [tevas]
        assert variklis.nustatyti_gavejus(AutomatizavimoTaisykle(gavejai="tevai"), posedis) == \
            [tevas, antras_tevas]
        assert variklis.nustatyti_gavejus(AutomatizavimoTaisykle(gavejai="nezinoma"), posedis) == []

    @pytest.mark.parametrize("salyga, gera", [
        (None, True),
        ({"matomas_tevams": True}, True),
        ({"kategorija": ["a", "b"]}, True),
        ([1, 2], False),
        ({"laukas": {"gilus": 1}}, False),
        ({"_privatus": 1}, False),
    ])
    def test_salygos_patikra(self, salyga, gera):
        assert (patikrinti_salyga(salyga) is None) is gera


# --- Įvykių skirstytuvas (FR-A04, FR-A07, NFR-10) -----------------------------------

class TestIvykiuSkirstytuvas:
    def test_skelbimas_tevams_sukuria_po_pranesima_kiekvienam_tevui(
            self, numatytosios_taisykles, admin, tevas, antras_tevas):
        skelbimas = _skelbimas(admin)
        assert skelbti("skelbimas_paskelbtas", skelbimas) == 2
        db.session.commit()
        irasai = EilesIrasas.query.order_by(EilesIrasas.gavejo_id).all()
        assert [i.gavejo_id for i in irasai] == [tevas.id, antras_tevas.id]
        assert irasai[0].tema == "Naujas skelbimas: Atvirų durų diena"
        assert "Sveiki, Petras" in irasai[0].tekstas
        assert "http://mokykla.test/tevams/skelbimai" in irasai[0].tekstas  # nuoroda tėvui

    def test_salyga_netenkinama_pranesimu_nera(self, numatytosios_taisykles, admin, tevas):
        assert skelbti("skelbimas_paskelbtas", _skelbimas(admin, matomas_tevams=False)) == 0

    def test_tas_pats_ivykis_antra_karta_nesukuria_dublikatu(self, numatytosios_taisykles, admin, tevas):
        """FR-A04: tas pats pranešimas tam pačiam gavėjui sukuriamas tik kartą."""
        skelbimas = _skelbimas(admin)
        assert skelbti("skelbimas_paskelbtas", skelbimas) == 1
        db.session.commit()
        assert skelbti("skelbimas_paskelbtas", skelbimas) == 0
        assert EilesIrasas.query.count() == 1

    def test_naudotojas_atsisakes_el_laisku_ju_negauna(self, numatytosios_taisykles, admin, tevas,
                                                         antras_tevas):
        """FR-A07: el. laiškų galima atsisakyti."""
        db.session.add(PranesimuNustatymas(vartotojo_id=tevas.id, ivykio_tipas="skelbimas_paskelbtas",
                                           el_pastas=False))
        db.session.commit()
        assert skelbti("skelbimas_paskelbtas", _skelbimas(admin)) == 1
        assert EilesIrasas.query.one().gavejo_id == antras_tevas.id

    def test_privalomo_pranesimo_atsisakyti_negalima_ir_vgk_laiske_nera_esmes(
            self, numatytosios_taisykles, tevas, vaikas):
        """FR-A07 išimtis (VGK kvietimai privalomi) ir NFR-10 (be svarstymo esmės)."""
        db.session.add(PranesimuNustatymas(vartotojo_id=tevas.id, ivykio_tipas="vgk_posedis_suplanuotas",
                                           el_pastas=False))
        posedis = _posedis_su_dalyviu(tevas, date(2026, 12, 8))
        posedis.svarstymai.append(VgkSvarstymas(atvejis=VgkAtvejis(mokinio_id=vaikas.id,
                                                                    priezastis="Elgesio sunkumai")))
        db.session.commit()

        assert skelbti("vgk_posedis_suplanuotas", posedis) == 2  # el. paštas ir sistema
        laiskas = EilesIrasas.query.filter_by(kanalas="el_pastas").one()
        assert "2026-12-08" in laiskas.tekstas and "14:00" in laiskas.tekstas
        assert "Mokytojų kambarys" in laiskas.tekstas
        assert vaikas.pavarde not in laiskas.tekstas
        assert "Elgesio" not in laiskas.tekstas

    def test_sablono_klaida_praleidzia_taisykle_bet_ne_kitas(self, admin, tevas):
        geras = PranesimoSablonas(kodas="geras", pavadinimas="g", tema="Gera", tekstas="t")
        blogas = PranesimoSablonas(kodas="blogas", pavadinimas="b", tema="Bloga",
                                   tekstas="{{ ''.__class__.__mro__ }}")
        for sablonas in (blogas, geras):
            db.session.add(AutomatizavimoTaisykle(pavadinimas=sablonas.kodas, ivykio_tipas="skelbimas_paskelbtas",
                                                  gavejai="tevai", kanalas="el_pastas", sablonas=sablonas))
        db.session.commit()
        assert skelbti("skelbimas_paskelbtas", _skelbimas(admin)) == 1
        assert EilesIrasas.query.one().tema == "Gera"

    def test_nezinomas_ivykio_tipas(self, admin):
        with pytest.raises(ValueError):
            skelbti("neegzistuoja", _skelbimas(admin))

    def test_kontekste_tik_leistini_laukai(self, admin, tevas, mokytojas):
        """NFR-07: šablonui perduodami žodynai, o ne duomenų bazės objektai."""
        skelbimas = _skelbimas(admin)
        kontekstas = sukurti_konteksta(IVYKIU_TIPAI["skelbimas_paskelbtas"], skelbimas, tevas)
        assert set(kontekstas) == {"skelbimas", "gavejas", "mokykla", "nuoroda"}
        assert "slaptazodzio_hash" not in kontekstas["gavejas"]
        darbuotojui = sukurti_konteksta(IVYKIU_TIPAI["skelbimas_paskelbtas"], skelbimas, mokytojas)
        assert darbuotojui["nuoroda"] == f"http://mokykla.test/skelbimai/{skelbimas.id}"

    def test_nuoroda_i_dar_nesukurta_puslapi_veda_i_pradzia(self):
        assert kelias("nera.tokio_puslapio") == "/"


# --- Pranešimų eilė (FR-A05, FR-A08, FR-A09) ----------------------------------------

class TestPranesimuEile:
    def test_prideti_dublikatas_grazina_none(self, tevas):
        eile = PranesimuEile()
        assert eile.prideti(tevas, "el_pastas", "r1", "t", "t") is not None
        db.session.commit()
        assert eile.prideti(tevas, "el_pastas", "r1", "t", "t") is None
        db.session.commit()
        assert EilesIrasas.query.count() == 1

    def test_paima_iki_20_laukianciu_ir_pazymi_siunciamais(self, tevas):
        for nr in range(25):
            _irasas(tevas, f"r{nr}")
        _irasas(tevas, "ateitis", siusti_po=utc_dabar() + timedelta(hours=1))
        eile = PranesimuEile()

        pirma = eile.paimti_laukiancius()
        assert len(pirma) == 20
        assert all(i.busena == EilesIrasas.SIUNCIAMAS for i in pirma)
        antra = eile.paimti_laukiancius()
        assert len(antra) == 5  # ateities įrašas dar neimamas
        assert eile.paimti_laukiancius() == []

    @pytest.mark.parametrize("bandymas, intervalas", [
        (1, timedelta(minutes=5)), (2, timedelta(minutes=30)), (3, timedelta(hours=2)),
    ])
    def test_pakartojimas_po_5_min_30_min_ir_2_val(self, tevas, bandymas, intervalas):
        irasas = _irasas(tevas, "r", bandymai=bandymas - 1, busena=EilesIrasas.SIUNCIAMAS)
        pries = utc_dabar()
        PranesimuEile().atideti(irasas, "SMTP nepasiekiamas")
        assert irasas.busena == EilesIrasas.LAUKIA
        assert irasas.bandymai == bandymas
        assert pries + intervalas <= irasas.siusti_po <= utc_dabar() + intervalas
        assert irasas.klaida == "SMTP nepasiekiamas"

    def test_po_4_bandymo_nepavyko(self, tevas):
        irasas = _irasas(tevas, "r", bandymai=MAKS_BANDYMU - 1, busena=EilesIrasas.SIUNCIAMAS)
        PranesimuEile().atideti(irasas, "klaida")
        assert MAKS_BANDYMU == 4
        assert irasas.busena == EilesIrasas.NEPAVYKO

    def test_uzstrige_grazinami_i_eile(self, tevas):
        senas = _irasas(tevas, "senas", busena=EilesIrasas.SIUNCIAMAS,
                        siusti_po=utc_dabar() - timedelta(minutes=20))
        naujas = _irasas(tevas, "naujas", busena=EilesIrasas.SIUNCIAMAS,
                         siusti_po=utc_dabar() - timedelta(minutes=5))
        assert PranesimuEile().grazinti_uzstrigusius() == 1
        db.session.refresh(senas)
        db.session.refresh(naujas)
        assert senas.busena == EilesIrasas.LAUKIA
        assert naujas.busena == EilesIrasas.SIUNCIAMAS

    def test_atsaukiami_tik_to_objekto_neissiusti_pranesimai(self, tevas):
        """FR-A08: „renginys-1“ neturi paveikti „renginys-12“ pranešimų."""
        laukia = _irasas(tevas, "renginys-1/renginys_artejantis/t1/g1/el_pastas")
        issiustas = _irasas(tevas, "renginys-1/renginys_sukurtas/t2/g1/el_pastas",
                            busena=EilesIrasas.ISSIUSTAS)
        kitas = _irasas(tevas, "renginys-12/renginys_artejantis/t1/g1/el_pastas")
        assert PranesimuEile().atsaukti_objekto("renginys-1") == 1
        db.session.commit()
        for irasas in (laukia, issiustas, kitas):
            db.session.refresh(irasas)
        assert laukia.busena == EilesIrasas.ATSAUKTAS
        assert issiustas.busena == EilesIrasas.ISSIUSTAS
        assert kitas.busena == EilesIrasas.LAUKIA

    def test_pakartoti_tik_nepavykusi(self, tevas):
        """FR-A09: administratorius gali pakartoti nepavykusį siuntimą."""
        nepavykes = _irasas(tevas, "a", busena=EilesIrasas.NEPAVYKO, bandymai=4, klaida="x")
        issiustas = _irasas(tevas, "b", busena=EilesIrasas.ISSIUSTAS)
        eile = PranesimuEile()
        assert eile.pakartoti(nepavykes) is True
        assert (nepavykes.busena, nepavykes.bandymai, nepavykes.klaida) == (EilesIrasas.LAUKIA, 0, None)
        assert eile.pakartoti(issiustas) is False

    def test_statistika(self, tevas):
        _irasas(tevas, "a", busena=EilesIrasas.ISSIUSTAS, issiusta=utc_dabar())
        _irasas(tevas, "b")
        _irasas(tevas, "c", bandymai=1)
        _irasas(tevas, "d", busena=EilesIrasas.NEPAVYKO)
        assert PranesimuEile().statistika(utc_dabar() - timedelta(hours=24)) == \
            {"issiusta": 1, "laukia": 1, "kartojama": 1, "nepavyko": 1}


# --- Kanalai ------------------------------------------------------------------------

class _NetikrasSmtp:
    """smtplib.SMTP pakaitalas: įsimena kvietimus, tikro tinklo nenaudoja."""
    kvietimai = []
    klaida = None

    def __init__(self, serveris, prievadas, timeout):
        _NetikrasSmtp.kvietimai.append(("jungtis", serveris, prievadas))
        if _NetikrasSmtp.klaida:
            raise _NetikrasSmtp.klaida

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        _NetikrasSmtp.kvietimai.append(("starttls",))

    def login(self, vartotojas, slaptazodis):
        _NetikrasSmtp.kvietimai.append(("login", vartotojas))

    def send_message(self, laiskas):
        _NetikrasSmtp.kvietimai.append(("send", laiskas["To"], laiskas["Subject"]))


class TestKanalai:
    def test_el_laiskas_irasomas_i_faila_kurimo_aplinkoje(self, tevas, laisku_katalogas):
        irasas = _irasas(tevas, "r", tema="Kvietimas į posėdį")
        ElPastoKanalas().siusti(irasas)
        failai = os.listdir(laisku_katalogas)
        assert len(failai) == 1
        turinys = (laisku_katalogas / failai[0]).read_bytes().decode("utf-8")
        assert "To: tevas@test.lt" in turinys
        assert "Auto-Submitted: auto-generated" in turinys

    def test_siuntimas_per_smtp(self, tevas, monkeypatch):
        _NetikrasSmtp.kvietimai, _NetikrasSmtp.klaida = [], None
        monkeypatch.setattr(smtplib, "SMTP", _NetikrasSmtp)
        kanalas = ElPastoKanalas({"MAIL_BACKEND": "smtp", "MAIL_SERVER": "smtp.test", "MAIL_PORT": 587,
                                  "MAIL_USE_TLS": True, "MAIL_USERNAME": "mokykla", "MAIL_PASSWORD": "x",
                                  "MAIL_SENDER": "Mokykla <noreply@mokykla.test>"})
        assert kanalas.siusti(_irasas(tevas, "r")) is True
        assert [k[0] for k in _NetikrasSmtp.kvietimai] == ["jungtis", "starttls", "login", "send"]
        assert _NetikrasSmtp.kvietimai[-1][1] == "tevas@test.lt"

    def test_smtp_klaida_tampa_siuntimo_klaida(self, tevas, monkeypatch):
        _NetikrasSmtp.kvietimai, _NetikrasSmtp.klaida = [], ConnectionRefusedError("atmesta")
        monkeypatch.setattr(smtplib, "SMTP", _NetikrasSmtp)
        kanalas = ElPastoKanalas({"MAIL_BACKEND": "smtp", "MAIL_SERVER": "smtp.test"})
        with pytest.raises(SiuntimoKlaida):
            kanalas.siusti(_irasas(tevas, "r"))
        _NetikrasSmtp.klaida = None

    def test_be_serverio_siuntimo_klaida(self, tevas):
        with pytest.raises(SiuntimoKlaida, match="MAIL_SERVER"):
            ElPastoKanalas({"MAIL_BACKEND": "smtp", "MAIL_SERVER": None}).siusti(_irasas(tevas, "r"))

    def test_sistemos_kanalas_sukuria_pranesima_su_ikona(self, numatytosios_taisykles, tevas):
        irasas = _irasas(tevas, "r", kanalas="sistema",
                         taisykles_id=numatytosios_taisykles["skelbimas_paskelbtas"].id)
        SistemosKanalas().siusti(irasas)
        db.session.commit()
        pranesimas = Pranesimas.query.one()
        assert (pranesimas.vartotojo_id, pranesimas.ikona) == (tevas.id, "megaphone")
        assert SistemosKanalas.ikona(_irasas(tevas, "be-taisykles", kanalas="sistema")) == "bell"


# --- Siuntėjas (FR-A05) ---------------------------------------------------------------

class _LuztantisKanalas(Kanalas):
    kodas = "el_pastas"

    def siusti(self, irasas):
        raise SiuntimoKlaida("SMTP serveris nepasiekiamas")


class TestPranesimuSiuntejas:
    def test_issiuncia_abiem_kanalais(self, tevas, laisku_katalogas):
        _irasas(tevas, "a", kanalas="el_pastas")
        _irasas(tevas, "b", kanalas="sistema")
        assert PranesimuSiuntejas().siusti_partija() == 2
        assert {i.busena for i in EilesIrasas.query} == {EilesIrasas.ISSIUSTAS}
        assert all(i.bandymai == 1 and i.issiusta is not None for i in EilesIrasas.query)
        assert Pranesimas.query.count() == 1
        assert len(os.listdir(laisku_katalogas)) == 1

    def test_nepavykes_kartojamas_o_po_4_bandymu_informuojamas_administratorius(self, admin, tevas):
        irasas = _irasas(tevas, "a")
        siuntejas = PranesimuSiuntejas(kanalai=[_LuztantisKanalas()])
        for bandymas in range(1, MAKS_BANDYMU + 1):
            assert siuntejas.siusti_partija() == 0
            irasas = db.session.get(EilesIrasas, irasas.id)
            assert irasas.bandymai == bandymas
            if irasas.busena == EilesIrasas.LAUKIA:
                irasas.siusti_po = utc_dabar() - timedelta(seconds=1)  # „praleidžiame“ laukimą
                db.session.commit()
        assert irasas.busena == EilesIrasas.NEPAVYKO
        ispejimas = Pranesimas.query.filter_by(vartotojo_id=admin.id).one()
        assert ispejimas.pavadinimas == "Pranešimo išsiųsti nepavyko"
        assert ispejimas.nuoroda == "/automatizavimas/zurnalas?busena=nepavyko"

    def test_nezinomas_kanalas_laikomas_klaida(self, tevas):
        _irasas(tevas, "a", kanalas="sms")
        assert PranesimuSiuntejas().siusti_partija() == 0
        irasas = EilesIrasas.query.one()
        assert irasas.busena == EilesIrasas.LAUKIA
        assert "Nežinomas kanalas" in irasas.klaida


# --- Priminimai (FR-A06) ------------------------------------------------------------------

class TestPriminimai:
    def test_priminimas_apie_rytojaus_rengini(self, numatytosios_taisykles, mokytojas, tevas):
        siandien = date(2026, 12, 17)
        db.session.add_all([
            Renginys(pavadinimas="Kalėdinis koncertas", pradzios_data=date(2026, 12, 18),
                     matomas_tevams=True, vartotojo_id=mokytojas.id),
            Renginys(pavadinimas="Po trijų dienų", pradzios_data=date(2026, 12, 20),
                     matomas_tevams=True, vartotojo_id=mokytojas.id),
            Renginys(pavadinimas="Tik darbuotojams", pradzios_data=date(2026, 12, 18),
                     matomas_tevams=False, vartotojo_id=mokytojas.id),
        ])
        db.session.commit()
        kurejas = PriminimuKurejas()
        assert kurejas.sukurti_priminimus(siandien) == 1
        irasas = EilesIrasas.query.one()
        assert irasas.tema == "Primename: Kalėdinis koncertas (2026-12-18)"
        assert irasas.unikalus_raktas.endswith("/2026-12-18")
        # Antras paleidimas tą pačią dieną dublikatų nesukuria
        assert kurejas.sukurti_priminimus(siandien) == 0

    def test_posedzio_priminimas_likus_1_darbo_dienai(self, numatytosios_taisykles, tevas):
        _posedis_su_dalyviu(tevas, date(2026, 11, 30))  # pirmadienis
        kurejas = PriminimuKurejas()
        assert kurejas.sukurti_priminimus(date(2026, 11, 26)) == 0  # ketvirtadienis – liko 2
        assert kurejas.sukurti_priminimus(date(2026, 11, 27)) == 2  # penktadienis – liko 1 (el. paštas ir sistema)

    def test_atsauktam_posedziui_priminimo_nera(self, numatytosios_taisykles, tevas):
        _posedis_su_dalyviu(tevas, date(2026, 11, 30), busena=VgkPosedis.ATSAUKTAS)
        assert PriminimuKurejas().sukurti_priminimus(date(2026, 11, 27)) == 0

    def test_priemones_termino_priminimas_atsakingam(self, numatytosios_taisykles, mokytojas, vaikas):
        svarstymas = VgkSvarstymas(posedis=VgkPosedis(data=date(2026, 11, 10), laikas=time(14, 0), vieta="x"),
                                   atvejis=VgkAtvejis(mokinio_id=vaikas.id, priezastis="x"))
        db.session.add(svarstymas)
        svarstymas.priemones.append(VgkPriemone(atsakingo_id=mokytojas.id, aprasymas="Konsultacijos",
                                                terminas=date(2026, 12, 2)))
        db.session.commit()
        assert PriminimuKurejas().sukurti_priminimus(date(2026, 11, 30)) == 1  # liko 2 darbo dienos
        irasas = EilesIrasas.query.one()
        assert (irasas.gavejo_id, irasas.kanalas) == (mokytojas.id, "sistema")


class TestPlanuoklesUzduotys:
    def test_uzregistruotos_siuntimo_ir_priminimu_uzduotys(self, app):
        from apscheduler.schedulers.background import BackgroundScheduler
        uzduotys = {u.id: u for u in Planuokle(app, planuokle=BackgroundScheduler()).registruoti_uzduotis()}
        assert {"pranesimu_siuntimas", "priminimai", "busenos_patikra"} <= set(uzduotys)
        assert uzduotys["pranesimu_siuntimas"].trigger.interval == timedelta(minutes=1)
        assert "hour='7'" in str(uzduotys["priminimai"].trigger)
