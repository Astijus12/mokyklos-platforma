"""Alembic migracijų testai su laikina SQLite duomenų baze (failas tmp_path kataloge).

Tikrinami trys paleidimo atvejai iš db_atnaujinimas.py: tuščia duomenų bazė,
sena duomenų bazė be Alembic ir duomenų perkėlimas iš mokiniai.geroves_* į
vgk_atvejai (migracija 0003), taip pat migracijų atšaukimas.
"""
from datetime import date, datetime

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text

from app import create_app
from config import TestConfig
from db_atnaujinimas import ar_schema_naujausia, atnaujinti_duomenu_baze, dabartine_ir_naujausia_versija
from models import Mokinys, VgkAtvejis, db

pytestmark = pytest.mark.migracijos

SENI_VGK_STULPELIAI = {"geroves_komisija", "geroves_komisija_data", "geroves_komisija_pastabos"}


@pytest.fixture
def migracijos_app(tmp_path):
    """Atskira programa su tuščia SQLite duomenų baze faile (ne atmintyje)."""
    class MigracijuKonfiguracija(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'migracijos.db').as_posix()}"

    programa = create_app(MigracijuKonfiguracija)
    with programa.app_context():
        yield programa
        db.session.remove()
        db.engine.dispose()


def _lenteles():
    return set(inspect(db.engine).get_table_names()) - {"alembic_version"}


def _stulpeliai(lentele):
    return {s["name"] for s in inspect(db.engine).get_columns(lentele)}


def _irasyti_senus_mokinius():
    """Mokiniai su VGK duomenimis taip, kaip juos saugojo praktikų versija."""
    with db.engine.begin() as rysys:
        rysys.execute(text("INSERT INTO klases (id, pavadinimas, mokslo_metai) VALUES (1, '5A', '2025-2026')"))
        rysys.execute(text(
            "INSERT INTO mokiniai (id, vardas, pavarde, klases_id, mokyklos_autobusas, geroves_komisija, "
            "geroves_komisija_data, geroves_komisija_pastabos) VALUES "
            "(1, 'Domas', 'Butkus', 1, 0, 1, '2025-10-15', 'Aptarta adaptacijos eiga'), "
            "(2, 'Justas', 'Gricius', 1, 0, 1, NULL, NULL), "
            "(3, 'Eglė', 'Čepaitė', 1, 0, 0, '2024-05-01', 'Sena istorija'), "
            "(4, 'Ieva', 'Eidukaitė', 1, 0, 0, NULL, NULL)"
        ))


@pytest.mark.parametrize("adresas, tiketina", [
    ("postgres://u:s@host:5432/db", "postgresql+psycopg2://u:s@host:5432/db"),        # Render, Heroku
    ("postgresql://u:s@host:5432/db", "postgresql+psycopg2://u:s@host:5432/db"),
    ("postgresql+psycopg2://u:s@host/db", "postgresql+psycopg2://u:s@host/db"),       # jau nurodyta
    ("sqlite:///mokykla.db", "sqlite:///mokykla.db"),
    (None, None),
], ids=["postgres", "postgresql", "su_tvarkykle", "sqlite", "nenurodyta"])
def test_db_adresui_nurodoma_tvarkykle(adresas, tiketina):
    """Render diegimas nepavyko: be nurodytos tvarkyklės naujesnė SQLAlchemy rinkosi psycopg (3)."""
    from config import normalizuoti_db_adresa
    assert normalizuoti_db_adresa(adresas) == tiketina


class TestTusciaDuomenuBaze:
    def test_sukuriamos_visos_lenteles(self, migracijos_app):
        atnaujinti_duomenu_baze()
        assert ar_schema_naujausia()
        assert len(_lenteles()) == 23
        assert "vgk_pareigos" in _stulpeliai("users")
        assert not SENI_VGK_STULPELIAI & _stulpeliai("mokiniai")

    def test_versijos_iki_ir_po(self, migracijos_app):
        dabartine, naujausia = dabartine_ir_naujausia_versija()
        assert dabartine is None
        upgrade()
        assert dabartine_ir_naujausia_versija() == (naujausia, naujausia)


class TestVgkDuomenuPerkelimas:
    def test_geroves_zymes_tampa_vgk_atvejais(self, migracijos_app):
        upgrade(revision="0001")
        _irasyti_senus_mokinius()
        upgrade()

        atvejai = {a.mokinio_id: a for a in VgkAtvejis.query.all()}
        assert set(atvejai) == {1, 2, 3}  # Ieva be VGK duomenų – atvejo nėra

        domas = atvejai[1]
        assert domas.busena == VgkAtvejis.SVARSTOMAS
        assert domas.sukurta == datetime(2025, 10, 15)
        assert domas.priezastis == "Aptarta adaptacijos eiga"
        assert domas.pateike_id is None

        assert atvejai[2].busena == VgkAtvejis.SVARSTOMAS
        assert atvejai[2].priezastis.startswith("Perkelta iš mokinio kortelės")

        egle = atvejai[3]
        assert egle.busena == VgkAtvejis.UZBAIGTAS
        assert egle.uzbaigta == datetime(2024, 5, 1)

    def test_esami_puslapiai_mato_tas_pacias_reiksmes(self, migracijos_app):
        upgrade(revision="0001")
        _irasyti_senus_mokinius()
        upgrade()

        domas = db.session.get(Mokinys, 1)
        assert domas.geroves_komisija is True
        assert domas.geroves_komisija_data == date(2025, 10, 15)
        assert domas.geroves_komisija_pastabos == "Aptarta adaptacijos eiga"
        assert db.session.get(Mokinys, 3).geroves_komisija is False
        assert db.session.get(Mokinys, 4).geroves_komisija is False

    def test_atsaukimas_grazina_stulpelius_o_kartojimas_nedubliuoja(self, migracijos_app):
        upgrade(revision="0001")
        _irasyti_senus_mokinius()
        upgrade()
        downgrade(revision="0002")

        assert SENI_VGK_STULPELIAI <= _stulpeliai("mokiniai")
        with db.engine.connect() as rysys:
            eilutes = dict(rysys.execute(text(
                "SELECT id, geroves_komisija FROM mokiniai ORDER BY id")).fetchall())
        assert eilutes == {1: 1, 2: 1, 3: 0, 4: 0}

        upgrade()
        assert VgkAtvejis.query.count() == 3

    def test_pilnas_atsaukimas_iki_pradzios(self, migracijos_app):
        upgrade()
        downgrade(revision="base")
        assert _lenteles() == set()


class TestSenaDuomenuBaze:
    def test_sena_db_be_alembic_papildoma_ir_atnaujinama(self, migracijos_app):
        # Imituojama praktikų versijos duomenų bazė: lentelės yra, migracijų istorijos nėra,
        # trūksta vėliau pridėto stulpelio ir lentelės
        upgrade(revision="0001")
        _irasyti_senus_mokinius()
        with db.engine.begin() as rysys:
            rysys.execute(text("DROP TABLE alembic_version"))
            rysys.execute(text("DROP TABLE pranesimai"))
            rysys.execute(text("ALTER TABLE skelbimai DROP COLUMN kategorija"))

        atnaujinti_duomenu_baze()

        assert ar_schema_naujausia()
        assert "pranesimai" in _lenteles()
        assert "kategorija" in _stulpeliai("skelbimai")
        assert VgkAtvejis.query.count() == 3

    def test_kartotinis_paleidimas_nieko_nekeicia(self, migracijos_app):
        atnaujinti_duomenu_baze()
        atnaujinti_duomenu_baze()
        assert ar_schema_naujausia()
        assert len(_lenteles()) == 23
