"""Duomenų bazės schemos paruošimas paleidžiant programą (Alembic migracijos).

Funkcija atnaujinti_duomenu_baze() atpažįsta tris atvejus:

1. Tuščia duomenų bazė – įvykdomos visos migracijos (0001, 0002, 0003, ...).
2. Sena duomenų bazė, sukurta praktikų versijos be Alembic (yra lentelė users,
   bet nėra alembic_version). Pirmiausia ji papildoma iki pradinės schemos
   (anksčiau tai darė wsgi.py ir migruoti_tevu_portala.py rankinėmis ALTER
   TABLE komandomis), pažymima versija 0001 ir tik tada vykdomos naujos
   migracijos. Taip seni duomenys, pvz., mokinių VGK žymės, perkeliami į
   naujas lenteles.
3. Duomenų bazė jau valdoma Alembic – vykdomos tik dar neįvykdytos migracijos.

Visos funkcijos kviečiamos programos kontekste (with app.app_context()).
"""
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask import current_app
from flask_migrate import stamp, upgrade
from sqlalchemy import inspect, text

from models import db

PRADINE_VERSIJA = "0001"

# Stulpeliai, kurie praktikų versijoje buvo pridedami rankinėmis ALTER TABLE komandomis
_SENI_STULPELIAI = [
    ("users", "telefonas", "VARCHAR(30)"),
    ("users", "dvfa_paslaptis", "VARCHAR(64)"),
    ("users", "dvfa_ijungtas", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "api_token_hash", "VARCHAR(128)"),
    ("users", "api_token_data", "TIMESTAMP"),
    ("skelbimai", "matomas_tevams", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("skelbimai", "kategorija", "VARCHAR(30) NOT NULL DEFAULT 'bendra'"),
    ("mokiniai", "nuotraukos_failas", "VARCHAR(300)"),
]

# Lentelės, kurias praktikų versija sukurdavo db.create_all(), jei jų dar nebuvo
_SENOS_LENTELES = ["tevu_vaiku_rysys", "renginiai", "veiklos_zurnalas", "pranesimai"]


def _yra_sena_be_alembic():
    lenteles = set(inspect(db.engine).get_table_names())
    return "users" in lenteles and "alembic_version" not in lenteles


def _papildyti_iki_pradines_schemos():
    """Seną duomenų bazę papildo trūkstamais praktikų laikų stulpeliais ir lentelėmis."""
    inspector = inspect(db.engine)
    for lentele, stulpelis, tipas in _SENI_STULPELIAI:
        esami = {s["name"] for s in inspector.get_columns(lentele)}
        if stulpelis not in esami:
            with db.engine.begin() as rysys:
                rysys.execute(text(f"ALTER TABLE {lentele} ADD COLUMN {stulpelis} {tipas}"))
            print(f"  + {lentele}.{stulpelis}")
    for pavadinimas in _SENOS_LENTELES:
        db.metadata.tables[pavadinimas].create(bind=db.engine, checkfirst=True)


def atnaujinti_duomenu_baze():
    """Atnaujina duomenų bazės schemą iki naujausios migracijos."""
    if _yra_sena_be_alembic():
        print("Rasta duomenų bazė be migracijų istorijos: papildoma ir pažymima versija "
              f"{PRADINE_VERSIJA}.")
        _papildyti_iki_pradines_schemos()
        stamp(revision=PRADINE_VERSIJA)
    upgrade()


def dabartine_ir_naujausia_versija():
    """Grąžina porą (duomenų bazės versija, naujausia migracijų versija)."""
    migracijos = current_app.extensions["migrate"].migrate.get_config()
    naujausia = ScriptDirectory.from_config(migracijos).get_current_head()
    with db.engine.connect() as rysys:
        dabartine = MigrationContext.configure(rysys).get_current_revision()
    return dabartine, naujausia


def ar_schema_naujausia():
    """Ar duomenų bazėje įvykdytos visos migracijos (naudoja fono procesas)."""
    dabartine, naujausia = dabartine_ir_naujausia_versija()
    return dabartine == naujausia


def sukurti_schema_is_naujo():
    """Ištrina visas lenteles ir sukuria schemą migracijomis (demonstraciniams duomenims)."""
    db.drop_all()
    with db.engine.begin() as rysys:
        rysys.execute(text("DROP TABLE IF EXISTS alembic_version"))
    upgrade()
