"""Baigiamojo darbo modelių testai: 14 naujų lentelių, User ir Mokinys papildymai.

Tikrinama, kad modeliai atitinka ER diagramas: ryšiai, numatytosios reikšmės,
unikalumo ir CHECK apribojimai, sudėtiniai pirminiai raktai ir JSON laukai.
"""
from datetime import date, datetime, time

import pytest
from sqlalchemy.exc import IntegrityError

from models import (
    AutomatizavimoTaisykle,
    Dokumentas,
    DokumentuSkaitiklis,
    EilesIrasas,
    ImportoEilute,
    ImportoSesija,
    Mokinys,
    PazymosPrasymas,
    PranesimoSablonas,
    PranesimuNustatymas,
    User,
    VgkAtvejis,
    VgkDalyvis,
    VgkPosedis,
    VgkPriemone,
    VgkSvarstymas,
    db,
    utc_dabar,
)

pytestmark = pytest.mark.modelis


def _sablonas(kodas="skelbimas_tevams"):
    s = PranesimoSablonas(kodas=kodas, pavadinimas="Skelbimas tėvams",
                          tema="Naujas skelbimas", tekstas="{{ skelbimas.pavadinimas }}")
    db.session.add(s)
    db.session.commit()
    return s


def _eiles_irasas(gavejas, raktas="skelbimas-1/t1/g1/el_pastas"):
    return EilesIrasas(gavejo_id=gavejas.id, kanalas="el_pastas", tema="Tema",
                       tekstas="Tekstas", unikalus_raktas=raktas)


class TestUserPapildymai:
    def test_roles_pavadinimas_teisingomis_raidemis(self, admin, mokytojas, tevas):
        assert tevas.roles_pavadinimas == "Tėvas"
        assert mokytojas.roles_pavadinimas == "Mokytojas"
        assert admin.roles_pavadinimas == "Administratorius"

    def test_vgk_pareigos_numatytai_tuscios(self, mokytojas):
        assert mokytojas.vgk_pareigos is None
        assert mokytojas.yra_vgk_narys is False
        assert mokytojas.gali_planuoti_vgk_posedzius is False

    @pytest.mark.parametrize("pareigos, narys, planuoja", [
        ("narys", True, False),
        ("pirmininkas", True, True),
        ("sekretorius", True, True),
    ])
    def test_vgk_pareigu_teises(self, db_session, mokytojas, pareigos, narys, planuoja):
        mokytojas.vgk_pareigos = pareigos
        db_session.commit()
        assert mokytojas.yra_vgk_narys is narys
        assert mokytojas.gali_planuoti_vgk_posedzius is planuoja


class TestVgkAtvejis:
    def test_numatytoji_busena_uzregistruotas(self, db_session, vaikas, mokytojas):
        a = VgkAtvejis(mokinio_id=vaikas.id, pateike_id=mokytojas.id, priezastis="Mokymosi sunkumai")
        db_session.add(a)
        db_session.commit()
        assert a.busena == VgkAtvejis.UZREGISTRUOTAS
        assert a.busenos_pavadinimas == "Užregistruotas"
        assert a.sukurta is not None
        assert a.yra_aktyvus is True
        assert a.pateike == mokytojas

    def test_check_apribojimas_neleidzia_neleistinos_busenos(self, db_session, vaikas):
        db_session.add(VgkAtvejis(mokinio_id=vaikas.id, priezastis="x", busena="pamirstas"))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_salinant_mokini_salinami_ir_atvejai(self, db_session, vaikas):
        db_session.add(VgkAtvejis(mokinio_id=vaikas.id, priezastis="x"))
        db_session.commit()
        db_session.delete(vaikas)
        db_session.commit()
        assert VgkAtvejis.query.count() == 0


class TestMokinioSuderinamumoSavybes:
    """Esami šablonai naudoja mokinys.geroves_komisija – dabar tai savybės iš vgk_atvejai."""

    def test_be_atveju_zymes_nera(self, vaikas):
        assert vaikas.geroves_komisija is False
        assert vaikas.geroves_komisija_data is None
        assert vaikas.geroves_komisija_pastabos is None

    def test_aktyvus_atvejis_rodomas_kaip_zyme(self, db_session, vaikas):
        db_session.add(VgkAtvejis(mokinio_id=vaikas.id, priezastis="Elgesio sunkumai",
                                  busena=VgkAtvejis.SVARSTOMAS, sukurta=datetime(2025, 10, 15, 9, 0)))
        db_session.commit()
        db_session.expire_all()
        mokinys = db_session.get(Mokinys, vaikas.id)
        assert mokinys.geroves_komisija is True
        assert mokinys.geroves_komisija_data == date(2025, 10, 15)
        assert mokinys.geroves_komisija_pastabos == "Elgesio sunkumai"

    def test_uzbaigtas_atvejis_zymes_nesuteikia(self, db_session, vaikas):
        db_session.add(VgkAtvejis(mokinio_id=vaikas.id, priezastis="Sena istorija",
                                  busena=VgkAtvejis.UZBAIGTAS, uzbaigta=utc_dabar()))
        db_session.commit()
        db_session.expire_all()
        assert db_session.get(Mokinys, vaikas.id).geroves_komisija is False

    def test_rodomas_naujausias_aktyvus_atvejis(self, db_session, vaikas):
        db_session.add_all([
            VgkAtvejis(mokinio_id=vaikas.id, priezastis="Senesnis", sukurta=datetime(2025, 1, 10)),
            VgkAtvejis(mokinio_id=vaikas.id, priezastis="Naujesnis", sukurta=datetime(2025, 9, 1)),
        ])
        db_session.commit()
        db_session.expire_all()
        assert db_session.get(Mokinys, vaikas.id).geroves_komisija_pastabos == "Naujesnis"


class TestVgkPosedisIrSvarstymai:
    def _posedis(self, **kwargs):
        p = VgkPosedis(data=date(2026, 12, 8), laikas=time(14, 0), vieta="Mokytojų kambarys", **kwargs)
        db.session.add(p)
        db.session.commit()
        return p

    def test_posedzio_numatytoji_busena_juodrastis(self, db_session):
        p = self._posedis()
        assert p.busena == VgkPosedis.JUODRASTIS
        assert p.busenos_pavadinimas == "Juodraštis"
        assert p.skubos_priezastis is None

    def test_svarstymas_susieja_atveji_ir_posedi_su_priemonemis(self, db_session, vaikas, mokytojas):
        atvejis = VgkAtvejis(mokinio_id=vaikas.id, priezastis="Lankomumas")
        posedis = self._posedis()
        svarstymas = VgkSvarstymas(posedis=posedis, atvejis=atvejis, eiles_nr=1,
                                   nutarimas="Skirti socialinio pedagogo konsultacijas")
        db_session.add(svarstymas)
        svarstymas.priemones.append(VgkPriemone(atsakingo_id=mokytojas.id, aprasymas="Konsultacijos",
                                                terminas=date(2026, 12, 20)))
        db_session.commit()

        assert posedis.svarstymai[0].atvejis == atvejis
        assert atvejis.svarstymai[0].posedis == posedis
        priemone = svarstymas.priemones[0]
        assert priemone.busena == VgkPriemone.PASKIRTA
        assert priemone.atsakingas == mokytojas
        assert priemone.busenos_pavadinimas == "Paskirta"

    def test_tas_pats_atvejis_tame_paciame_posedyje_tik_karta(self, db_session, vaikas):
        atvejis = VgkAtvejis(mokinio_id=vaikas.id, priezastis="x")
        posedis = self._posedis()
        db_session.add_all([
            VgkSvarstymas(posedis=posedis, atvejis=atvejis, eiles_nr=1),
            VgkSvarstymas(posedis=posedis, atvejis=atvejis, eiles_nr=2),
        ])
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_dalyvis_naudotojas_ir_kviestinis(self, db_session, tevas):
        posedis = self._posedis()
        posedis.dalyviai.append(VgkDalyvis(vartotojo_id=tevas.id, vardas_pavarde=tevas.pilnas_vardas,
                                           vaidmuo="tevas"))
        posedis.dalyviai.append(VgkDalyvis(vardas_pavarde="Rasa Psichologė", vaidmuo="kviestinis"))
        db_session.commit()
        assert [d.vaidmens_pavadinimas for d in posedis.dalyviai] == ["Tėvas (globėjas)", "Kviestinis asmuo"]
        assert posedis.dalyviai[1].vartotojas is None
        assert posedis.dalyviai[0].dalyvavo is False
        assert posedis.dalyviai[0].pasizadejimas is False

    def test_salinant_posedi_salinami_svarstymai_ir_dalyviai(self, db_session, vaikas):
        posedis = self._posedis()
        posedis.svarstymai.append(VgkSvarstymas(atvejis=VgkAtvejis(mokinio_id=vaikas.id, priezastis="x")))
        posedis.dalyviai.append(VgkDalyvis(vardas_pavarde="Vardas", vaidmuo="narys"))
        db_session.commit()
        db_session.delete(posedis)
        db_session.commit()
        assert VgkSvarstymas.query.count() == 0
        assert VgkDalyvis.query.count() == 0
        assert VgkAtvejis.query.count() == 1  # atvejis lieka


class TestDokumentai:
    def test_dokumento_numeris_unikalus(self, db_session, admin):
        for _ in range(2):
            db_session.add(Dokumentas(numeris="PZ-2026-0001", tipas="PZ", sukure_id=admin.id,
                                      failo_kelias="dokumentai/PZ-2026-0001.pdf", sha256="a" * 64))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_tipo_pavadinimas(self, db_session):
        d = Dokumentas(numeris="PR-2026-0001", tipas="PR", failo_kelias="x.pdf", sha256="b" * 64)
        db_session.add(d)
        db_session.commit()
        assert d.tipo_pavadinimas == "VGK posėdžio protokolas"
        assert d.sukurta is not None

    def test_skaitiklio_sudetinis_raktas(self, db_session):
        db_session.add_all([
            DokumentuSkaitiklis(tipas="PZ", metai=2026, paskutinis_nr=41),
            DokumentuSkaitiklis(tipas="PZ", metai=2027),
            DokumentuSkaitiklis(tipas="PR", metai=2026),
        ])
        db_session.commit()
        assert db_session.get(DokumentuSkaitiklis, ("PZ", 2026)).paskutinis_nr == 41
        assert db_session.get(DokumentuSkaitiklis, ("PZ", 2027)).paskutinis_nr == 0

        db_session.add(DokumentuSkaitiklis(tipas="PZ", metai=2026))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_pazymos_prasymas_su_dokumentu(self, db_session, tevas, vaikas, admin):
        dok = Dokumentas(numeris="PZ-2026-0042", tipas="PZ", mokinio_id=vaikas.id,
                         failo_kelias="x.pdf", sha256="c" * 64)
        prasymas = PazymosPrasymas(tevo_id=tevas.id, mokinio_id=vaikas.id, paskirtis="Sporto būrelis")
        db_session.add_all([dok, prasymas])
        db_session.commit()
        assert prasymas.busena == PazymosPrasymas.PATEIKTAS
        assert prasymas.busenos_pavadinimas == "Pateiktas"

        prasymas.busena = PazymosPrasymas.IVYKDYTAS
        prasymas.nagrinejo_id = admin.id
        prasymas.dokumento_id = dok.id
        db_session.commit()
        assert prasymas.dokumentas.numeris == "PZ-2026-0042"
        assert prasymas.tevas == tevas and prasymas.nagrinejo == admin


class TestAutomatizavimas:
    def test_taisykle_su_keliais_kanalais_ir_json_salyga(self, db_session):
        t = AutomatizavimoTaisykle(pavadinimas="Komisijos posėdžio kvietimas",
                                   ivykio_tipas="vgk_posedis_suplanuotas", gavejai="posedzio_dalyviai",
                                   kanalas="el_pastas, sistema", salyga={"busena": "suplanuotas"},
                                   sablonas=_sablonas("vgk_kvietimas"))
        db_session.add(t)
        db_session.commit()
        db_session.expire_all()
        t = db_session.get(AutomatizavimoTaisykle, t.id)
        assert t.kanalu_sarasas == ["el_pastas", "sistema"]
        assert t.salyga == {"busena": "suplanuotas"}
        assert t.aktyvi is True and t.poslinkis_d == 0
        assert t.sablonas.kodas == "vgk_kvietimas"

    def test_sablono_kodas_unikalus(self, db_session):
        _sablonas("dublis")
        db_session.add(PranesimoSablonas(kodas="dublis", pavadinimas="x", tema="x", tekstas="x"))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_eiles_iraso_numatytosios_reiksmes(self, db_session, tevas):
        irasas = _eiles_irasas(tevas)
        db_session.add(irasas)
        db_session.commit()
        assert irasas.busena == EilesIrasas.LAUKIA
        assert irasas.bandymai == 0
        assert irasas.siusti_po is not None and irasas.issiusta is None
        assert irasas.kanalo_pavadinimas == "El. paštas"
        assert irasas.busenos_pavadinimas == "Laukia"

    def test_tas_pats_pranesimas_neirasomas_du_kartus(self, db_session, tevas):
        """NFR-01: unikalus raktas neleidžia sukurti to paties pranešimo antrą kartą."""
        db_session.add(_eiles_irasas(tevas))
        db_session.commit()
        db_session.add(_eiles_irasas(tevas))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        assert EilesIrasas.query.count() == 1

    def test_eiles_busenos_check_apribojimas(self, db_session, tevas):
        irasas = _eiles_irasas(tevas)
        irasas.busena = "dingo"
        db_session.add(irasas)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_pranesimu_nustatymai_sudetinis_raktas(self, db_session, tevas):
        db_session.add_all([
            PranesimuNustatymas(vartotojo_id=tevas.id, ivykio_tipas="skelbimas_paskelbtas", el_pastas=False),
            PranesimuNustatymas(vartotojo_id=tevas.id, ivykio_tipas="renginys_artejantis"),
        ])
        db_session.commit()
        n = db_session.get(PranesimuNustatymas, (tevas.id, "skelbimas_paskelbtas"))
        assert n.el_pastas is False
        assert db_session.get(PranesimuNustatymas, (tevas.id, "renginys_artejantis")).el_pastas is True


class TestImportas:
    def test_sesija_su_eilutemis(self, db_session, admin):
        sesija = ImportoSesija(vartotojo_id=admin.id, failo_vardas="mokiniai_2026.xlsx")
        sesija.eilutes.append(ImportoEilute(eilutes_nr=3, busena=ImportoEilute.KLAIDA,
                                            duomenys={"vardas": "Ona", "klase": "9Z"},
                                            klaidos="Klasė 9Z sistemoje nerasta"))
        sesija.eilutes.append(ImportoEilute(eilutes_nr=2, busena=ImportoEilute.TINKAMA,
                                            duomenys={"vardas": "Jonas", "gimimo_data": "2014-05-01"}))
        db_session.add(sesija)
        db_session.commit()
        db_session.expire_all()

        sesija = db_session.get(ImportoSesija, sesija.id)
        assert sesija.busena == ImportoSesija.PATIKRINTA
        assert [e.eilutes_nr for e in sesija.eilutes] == [2, 3]  # surikiuota pagal eilutės numerį
        assert sesija.eilutes[1].duomenys["klase"] == "9Z"
        assert sesija.eilutes[1].busenos_pavadinimas == "Klaida"

    def test_salinant_sesija_salinamos_eilutes(self, db_session):
        sesija = ImportoSesija(failo_vardas="a.csv")
        sesija.eilutes.append(ImportoEilute(eilutes_nr=2, busena="tinkama", duomenys={}))
        db_session.add(sesija)
        db_session.commit()
        db_session.delete(sesija)
        db_session.commit()
        assert ImportoEilute.query.count() == 0


class TestLenteliuSkaicius:
    def test_metaduomenyse_23_lenteles(self):
        """9 esamos ir 14 naujų lentelių (aprašo 1.8 poskyris)."""
        naujos = {
            "vgk_atvejai", "vgk_posedziai", "vgk_svarstymai", "vgk_dalyviai", "vgk_priemones",
            "dokumentai", "dokumentu_skaitikliai", "pazymu_prasymai",
            "automatizavimo_taisykles", "pranesimu_sablonai", "pranesimu_eile", "pranesimu_nustatymai",
            "importo_sesijos", "importo_eilutes",
        }
        lenteles = set(db.metadata.tables)
        assert naujos <= lenteles
        assert len(lenteles) == 23
        assert "vgk_pareigos" in db.metadata.tables["users"].c
        assert "geroves_komisija" not in db.metadata.tables["mokiniai"].c
