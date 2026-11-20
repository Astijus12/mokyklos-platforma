"""PostgreSQL testai: migracijos, jsonb, apribojimai ir SELECT ... FOR UPDATE SKIP LOCKED.

Šių savybių SQLite neturi, todėl jos tikrinamos tik su PostgreSQL
(pytest -m postgres, reikia TEST_DATABASE_URL).
"""
from datetime import datetime

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from db_atnaujinimas import ar_schema_naujausia
from models import EilesIrasas, VgkAtvejis, db


class TestSchemaPostgreSQL:
    def test_migracijos_sukure_visas_lenteles(self):
        assert ar_schema_naujausia()
        lenteles = set(inspect(db.engine).get_table_names()) - {"alembic_version"}
        assert len(lenteles) == 23

    def test_json_laukai_yra_jsonb(self):
        eilutes = db.session.execute(text(
            "SELECT table_name, column_name, data_type FROM information_schema.columns "
            "WHERE column_name IN ('salyga', 'duomenys') ORDER BY table_name"
        )).fetchall()
        assert [tuple(e) for e in eilutes] == [
            ("automatizavimo_taisykles", "salyga", "jsonb"),
            ("importo_eilutes", "duomenys", "jsonb"),
        ]

    def test_check_apribojimas_neleidzia_neleistinos_busenos(self, vaikas):
        db.session.add(VgkAtvejis(mokinio_id=vaikas.id, priezastis="x", busena="pamirstas"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_unikalus_raktas_neleidzia_dublikato(self, tevas):
        for _ in range(2):
            db.session.add(EilesIrasas(gavejo_id=tevas.id, kanalas="el_pastas", tema="t",
                                       tekstas="t", unikalus_raktas="renginys-1/t1/g1/el_pastas"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_salinant_naudotoja_jo_eiles_irasai_salinami(self, tevas):
        """Užsienio rakto ON DELETE CASCADE veikia duomenų bazės lygiu."""
        db.session.add(EilesIrasas(gavejo_id=tevas.id, kanalas="sistema", tema="t", tekstas="t",
                                   unikalus_raktas="r-1"))
        db.session.commit()
        with db.engine.begin() as rysys:
            rysys.execute(text("DELETE FROM tevu_vaiku_rysys"))
            rysys.execute(text("DELETE FROM users WHERE id = :id"), {"id": tevas.id})
        assert db.session.execute(text("SELECT count(*) FROM pranesimu_eile")).scalar() == 0


class TestSkipLocked:
    """Pranešimų eilė remiasi tuo, kad du siuntėjai negauna tų pačių įrašų (NFR-01)."""

    def test_du_lygiagretus_siuntejai_gauna_skirtingus_irasus(self, tevas):
        for nr in range(30):
            db.session.add(EilesIrasas(gavejo_id=tevas.id, kanalas="el_pastas", tema="t",
                                       tekstas="t", unikalus_raktas=f"bandymas-{nr}"))
        db.session.commit()
        db.session.remove()

        uzklausa = text(
            "SELECT id FROM pranesimu_eile WHERE busena = 'laukia' "
            "ORDER BY siusti_po, id LIMIT 20 FOR UPDATE SKIP LOCKED"
        )
        with db.engine.connect() as pirmas, db.engine.connect() as antras:
            pirmo_transakcija = pirmas.begin()
            antro_transakcija = antras.begin()
            pirmo_ids = [eil[0] for eil in pirmas.execute(uzklausa)]
            antro_ids = [eil[0] for eil in antras.execute(uzklausa)]
            pirmo_transakcija.rollback()
            antro_transakcija.rollback()

        assert len(pirmo_ids) == 20
        assert len(antro_ids) == 10
        assert not set(pirmo_ids) & set(antro_ids)


class TestVgkPerkelimasPostgreSQL:
    def test_migracija_0003_perkelia_geroves_duomenis(self):
        db.session.remove()
        downgrade(revision="0002")  # grąžinami seni mokiniai.geroves_* stulpeliai
        with db.engine.begin() as rysys:
            rysys.execute(text("INSERT INTO klases (id, pavadinimas, mokslo_metai) VALUES (1, '8B', '2025-2026')"))
            rysys.execute(text(
                "INSERT INTO mokiniai (id, vardas, pavarde, klases_id, mokyklos_autobusas, "
                "geroves_komisija, geroves_komisija_data, geroves_komisija_pastabos) VALUES "
                "(1, 'Justas', 'Gricius', 1, false, true, '2025-09-20', 'Matematikos sunkumai')"
            ))
        upgrade()

        atvejis = VgkAtvejis.query.one()
        assert atvejis.mokinio_id == 1
        assert atvejis.busena == VgkAtvejis.SVARSTOMAS
        assert atvejis.sukurta == datetime(2025, 9, 20)
        stulpeliai = {s["name"] for s in inspect(db.engine).get_columns("mokiniai")}
        assert "geroves_komisija" not in stulpeliai
        assert ar_schema_naujausia()
