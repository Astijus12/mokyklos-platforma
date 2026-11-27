"""Skubų VGK posėdį tvirtina administratorius: atmetimo priežastis ir pranešimai.

Jei iki posėdžio liko mažiau nei 5 darbo dienos, pirmininko ar sekretoriaus patvirtintas
posėdis laukia administratoriaus patvirtinimo (FR-V04). Administratoriui apie tai pranešama,
o atmetus – pirmininkui ir sekretoriui; atmetimo priežastis saugoma posėdžio įraše.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-27 13:30:00
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
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

PABAIGA = "\n\nŠis laiškas išsiųstas automatiškai, į jį atsakyti nereikia."

# Laiškuose nėra nei skubos, nei atmetimo priežasties – jos matomos tik sistemoje (NFR-10)
SABLONAI = [
    ("vgk_skubus_tvirtinti", "Skubus posėdis laukia patvirtinimo",
     "Laukia patvirtinimo skubus Vaiko gerovės komisijos posėdis {{ posedis.data }}",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "suplanuotas Vaiko gerovės komisijos posėdis {{ posedis.data }} {{ posedis.laikas }} val. "
     "(vieta: {{ posedis.vieta }}). Iki jo liko mažiau nei 5 darbo dienos, todėl posėdį turi patvirtinti "
     "administratorius – kvietimai dalyviams bus išsiųsti tik jį patvirtinus.\n\n"
     "Skubos priežastį matysite ir posėdį patvirtinti arba atmesti galėsite sistemoje: {{ nuoroda }}\n"
     "Dėl duomenų apsaugos skubos priežastis el. laiške nepateikiama." + PABAIGA),
    ("vgk_skubus_atmestas", "Skubus posėdis atmestas",
     "Nepatvirtintas skubus Vaiko gerovės komisijos posėdis {{ posedis.data }}",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "administratorius nepatvirtino skubaus Vaiko gerovės komisijos posėdžio, numatyto "
     "{{ posedis.data }} {{ posedis.laikas }} val. Kvietimai neišsiųsti, posėdis grąžintas į juodraščius.\n\n"
     "Atmetimo priežastį matysite ir kitą datą pasirinkti galėsite sistemoje: {{ nuoroda }}" + PABAIGA),
]
# (pavadinimas, įvykio tipas, sąlyga, gavėjai, kanalai, poslinkis, šablono kodas, aktyvi)
TAISYKLES = [
    ("Skubus posėdis laukia patvirtinimo", "vgk_posedis_laukia_patvirtinimo", None, "administratoriai",
     "el_pastas,sistema", 0, "vgk_skubus_tvirtinti", True),
    ("Skubus posėdis atmestas", "vgk_posedis_atmestas", None, "vgk_valdytojai",
     "el_pastas,sistema", 0, "vgk_skubus_atmestas", True),
]


def upgrade():
    with op.batch_alter_table("vgk_posedziai") as lentele:
        lentele.add_column(sa.Column("atmetimo_priezastis", sa.Text(), nullable=True))

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
    with op.batch_alter_table("vgk_posedziai") as lentele:
        lentele.drop_column("atmetimo_priezastis")
