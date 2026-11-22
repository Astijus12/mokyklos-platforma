"""Kvietimo į tėvų portalą šablonas ir taisyklė (importas, FR-I06).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-22 18:00:00
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

pranesimu_sablonai = sa.table(
    "pranesimu_sablonai",
    sa.column("id", sa.Integer), sa.column("kodas", sa.String), sa.column("pavadinimas", sa.String),
    sa.column("tema", sa.String), sa.column("tekstas", sa.Text), sa.column("atnaujinta", sa.DateTime),
)
automatizavimo_taisykles = sa.table(
    "automatizavimo_taisykles",
    sa.column("pavadinimas", sa.String), sa.column("ivykio_tipas", sa.String), sa.column("salyga", sa.JSON),
    sa.column("gavejai", sa.String), sa.column("kanalas", sa.String), sa.column("poslinkis_d", sa.Integer),
    sa.column("sablono_id", sa.Integer), sa.column("aktyvi", sa.Boolean),
)

SABLONAI = [
    ("tevo_kvietimas", "Kvietimas į tėvų portalą",
     "Kvietimas prisijungti prie {{ mokykla.pavadinimas }} tėvų portalo",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "{{ mokykla.pavadinimas }} sukūrė Jums paskyrą tėvų portale ({{ paskyra.el_pastas }}). "
     "Portale matysite vaiko duomenis, skelbimus, renginius ir galėsite užsakyti pažymas.\n\n"
     "Slaptažodį susikurkite paspaudę nuorodą (galioja 14 dienų):\n{{ nuoroda }}\n\n"
     "Šis laiškas išsiųstas automatiškai, į jį atsakyti nereikia."),
]
# (pavadinimas, įvykio tipas, sąlyga, gavėjai, kanalai, poslinkis, šablono kodas, aktyvi)
TAISYKLES = [
    ("Kvietimas į tėvų portalą", "tevo_paskyra_sukurta", None, "naujas_naudotojas", "el_pastas", 0,
     "tevo_kvietimas", True),
]


def upgrade():
    rysys = op.get_bind()
    esami = {eil.kodas for eil in rysys.execute(sa.select(pranesimu_sablonai.c.kodas))}
    dabar = datetime.now(timezone.utc).replace(tzinfo=None)
    nauji = [{"kodas": k, "pavadinimas": p, "tema": t, "tekstas": x, "atnaujinta": dabar}
             for k, p, t, x in SABLONAI if k not in esami]
    if nauji:
        op.bulk_insert(pranesimu_sablonai, nauji)
    sablonu_id = dict(rysys.execute(sa.select(pranesimu_sablonai.c.kodas, pranesimu_sablonai.c.id)).all())
    op.bulk_insert(automatizavimo_taisykles, [
        {"pavadinimas": p, "ivykio_tipas": t, "salyga": s, "gavejai": g, "kanalas": k, "poslinkis_d": d,
         "sablono_id": sablonu_id[kodas], "aktyvi": a}
        for p, t, s, g, k, d, kodas, a in TAISYKLES
    ])


def downgrade():
    rysys = op.get_bind()
    ids = [eil.id for eil in rysys.execute(
        sa.select(pranesimu_sablonai.c.id).where(pranesimu_sablonai.c.kodas.in_([s[0] for s in SABLONAI])))]
    if ids:
        rysys.execute(sa.text(
            "UPDATE pranesimu_eile SET taisykles_id = NULL WHERE taisykles_id IN "
            "(SELECT id FROM automatizavimo_taisykles WHERE sablono_id IN :ids)"
        ).bindparams(sa.bindparam("ids", expanding=True)), {"ids": ids})
        rysys.execute(automatizavimo_taisykles.delete().where(automatizavimo_taisykles.c.sablono_id.in_(ids)))
        rysys.execute(pranesimu_sablonai.delete().where(pranesimu_sablonai.c.id.in_(ids)))
