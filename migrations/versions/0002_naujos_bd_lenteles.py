"""Baigiamojo darbo lentelės: 14 naujų lentelių ir laukas users.vgk_pareigos.

Lentelės sugrupuotos pagal modulius (aprašo 1.8 poskyris, 10 ir 11 pav.):
- automatizavimas: pranesimu_sablonai, automatizavimo_taisykles, pranesimu_eile,
  pranesimu_nustatymai;
- dokumentai: dokumentai, dokumentu_skaitikliai, pazymu_prasymai;
- VGK: vgk_atvejai, vgk_posedziai, vgk_svarstymai, vgk_dalyviai, vgk_priemones;
- importas: importo_sesijos, importo_eilutes.

Duomenų perkėlimas iš mokiniai.geroves_* atliekamas kitoje migracijoje (0003),
kad schemos ir duomenų pakeitimai būtų atskirti.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-20 18:59:48
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# PostgreSQL – jsonb, SQLite – JSON (tekstas)
JSON_LAUKAS = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade():
    # --- Automatizavimas ------------------------------------------------------
    op.create_table(
        "pranesimu_sablonai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kodas", sa.String(length=50), nullable=False),
        sa.Column("pavadinimas", sa.String(length=200), nullable=False),
        sa.Column("tema", sa.String(length=200), nullable=False),
        sa.Column("tekstas", sa.Text(), nullable=False),
        sa.Column("atnaujinta", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kodas", name="uq_pranesimu_sablonai_kodas"),
    )

    op.create_table(
        "automatizavimo_taisykles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pavadinimas", sa.String(length=200), nullable=False),
        sa.Column("ivykio_tipas", sa.String(length=50), nullable=False),
        sa.Column("salyga", JSON_LAUKAS, nullable=True),
        sa.Column("gavejai", sa.String(length=50), nullable=False),
        sa.Column("kanalas", sa.String(length=50), nullable=False),
        sa.Column("poslinkis_d", sa.Integer(), nullable=False),
        sa.Column("sablono_id", sa.Integer(), nullable=False),
        sa.Column("aktyvi", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["sablono_id"], ["pranesimu_sablonai.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automatizavimo_taisykles_ivykio_tipas", "automatizavimo_taisykles", ["ivykio_tipas"])

    op.create_table(
        "pranesimu_eile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gavejo_id", sa.Integer(), nullable=False),
        sa.Column("taisykles_id", sa.Integer(), nullable=True),
        sa.Column("kanalas", sa.String(length=20), nullable=False),
        sa.Column("tema", sa.String(length=200), nullable=False),
        sa.Column("tekstas", sa.Text(), nullable=False),
        sa.Column("unikalus_raktas", sa.String(length=200), nullable=False),
        sa.Column("busena", sa.String(length=20), nullable=False),
        sa.Column("bandymai", sa.Integer(), nullable=False),
        sa.Column("siusti_po", sa.DateTime(), nullable=False),
        sa.Column("issiusta", sa.DateTime(), nullable=True),
        sa.Column("klaida", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "busena IN ('laukia', 'siunciamas', 'issiustas', 'nepavyko', 'atsauktas')",
            name="ck_pranesimu_eile_busena",
        ),
        sa.ForeignKeyConstraint(["gavejo_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["taisykles_id"], ["automatizavimo_taisykles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        # Tas pats pranešimas tam pačiam gavėjui įrašomas tik vieną kartą (NFR-01)
        sa.UniqueConstraint("unikalus_raktas", name="uq_pranesimu_eile_unikalus_raktas"),
    )
    op.create_index("ix_pranesimu_eile_busena_siusti_po", "pranesimu_eile", ["busena", "siusti_po"])
    op.create_index("ix_pranesimu_eile_gavejo_id", "pranesimu_eile", ["gavejo_id"])
    op.create_index("ix_pranesimu_eile_taisykles_id", "pranesimu_eile", ["taisykles_id"])

    op.create_table(
        "pranesimu_nustatymai",
        sa.Column("vartotojo_id", sa.Integer(), nullable=False),
        sa.Column("ivykio_tipas", sa.String(length=50), nullable=False),
        sa.Column("el_pastas", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["vartotojo_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vartotojo_id", "ivykio_tipas"),
    )

    # --- Dokumentai -----------------------------------------------------------
    op.create_table(
        "dokumentai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numeris", sa.String(length=30), nullable=False),
        sa.Column("tipas", sa.String(length=10), nullable=False),
        sa.Column("mokinio_id", sa.Integer(), nullable=True),
        sa.Column("sukure_id", sa.Integer(), nullable=True),
        sa.Column("failo_kelias", sa.String(length=300), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("sukurta", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["mokinio_id"], ["mokiniai.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sukure_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numeris", name="uq_dokumentai_numeris"),
    )
    op.create_index("ix_dokumentai_mokinio_id", "dokumentai", ["mokinio_id"])
    op.create_index("ix_dokumentai_sukurta", "dokumentai", ["sukurta"])
    op.create_index("ix_dokumentai_tipas", "dokumentai", ["tipas"])

    op.create_table(
        "dokumentu_skaitikliai",
        sa.Column("tipas", sa.String(length=10), nullable=False),
        sa.Column("metai", sa.Integer(), nullable=False),
        sa.Column("paskutinis_nr", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("tipas", "metai"),
    )

    op.create_table(
        "pazymu_prasymai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tevo_id", sa.Integer(), nullable=False),
        sa.Column("mokinio_id", sa.Integer(), nullable=False),
        sa.Column("paskirtis", sa.String(length=200), nullable=False),
        sa.Column("busena", sa.String(length=20), nullable=False),
        sa.Column("nagrinejo_id", sa.Integer(), nullable=True),
        sa.Column("dokumento_id", sa.Integer(), nullable=True),
        sa.Column("pateikta", sa.DateTime(), nullable=False),
        sa.Column("atmetimo_priezastis", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["dokumento_id"], ["dokumentai.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mokinio_id"], ["mokiniai.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["nagrinejo_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tevo_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pazymu_prasymai_busena", "pazymu_prasymai", ["busena"])
    op.create_index("ix_pazymu_prasymai_mokinio_id", "pazymu_prasymai", ["mokinio_id"])
    op.create_index("ix_pazymu_prasymai_tevo_id", "pazymu_prasymai", ["tevo_id"])

    # --- Vaiko gerovės komisija -----------------------------------------------
    op.create_table(
        "vgk_atvejai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mokinio_id", sa.Integer(), nullable=False),
        sa.Column("pateike_id", sa.Integer(), nullable=True),
        sa.Column("priezastis", sa.Text(), nullable=False),
        sa.Column("busena", sa.String(length=30), nullable=False),
        sa.Column("sukurta", sa.DateTime(), nullable=False),
        sa.Column("uzbaigta", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "busena IN ('uzregistruotas', 'svarstomas', 'taikomos_priemones', 'uzbaigtas')",
            name="ck_vgk_atvejai_busena",
        ),
        sa.ForeignKeyConstraint(["mokinio_id"], ["mokiniai.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pateike_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vgk_atvejai_busena", "vgk_atvejai", ["busena"])
    op.create_index("ix_vgk_atvejai_mokinio_id", "vgk_atvejai", ["mokinio_id"])
    op.create_index("ix_vgk_atvejai_pateike_id", "vgk_atvejai", ["pateike_id"])

    op.create_table(
        "vgk_posedziai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("laikas", sa.Time(), nullable=False),
        sa.Column("vieta", sa.String(length=200), nullable=False),
        sa.Column("busena", sa.String(length=30), nullable=False),
        sa.Column("skubos_priezastis", sa.Text(), nullable=True),
        sa.Column("protokolo_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["protokolo_id"], ["dokumentai.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vgk_posedziai_busena", "vgk_posedziai", ["busena"])
    op.create_index("ix_vgk_posedziai_data", "vgk_posedziai", ["data"])

    op.create_table(
        "vgk_svarstymai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("posedzio_id", sa.Integer(), nullable=False),
        sa.Column("atvejo_id", sa.Integer(), nullable=False),
        sa.Column("eiles_nr", sa.Integer(), nullable=False),
        sa.Column("nutarimas", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["atvejo_id"], ["vgk_atvejai.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["posedzio_id"], ["vgk_posedziai.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("posedzio_id", "atvejo_id", name="uq_vgk_svarstymai_posedis_atvejis"),
    )
    op.create_index("ix_vgk_svarstymai_atvejo_id", "vgk_svarstymai", ["atvejo_id"])
    op.create_index("ix_vgk_svarstymai_posedzio_id", "vgk_svarstymai", ["posedzio_id"])

    op.create_table(
        "vgk_dalyviai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("posedzio_id", sa.Integer(), nullable=False),
        sa.Column("vartotojo_id", sa.Integer(), nullable=True),
        sa.Column("vardas_pavarde", sa.String(length=160), nullable=False),
        sa.Column("vaidmuo", sa.String(length=30), nullable=False),
        sa.Column("dalyvavo", sa.Boolean(), nullable=False),
        sa.Column("pasizadejimas", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["posedzio_id"], ["vgk_posedziai.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vartotojo_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vgk_dalyviai_posedzio_id", "vgk_dalyviai", ["posedzio_id"])
    op.create_index("ix_vgk_dalyviai_vartotojo_id", "vgk_dalyviai", ["vartotojo_id"])

    op.create_table(
        "vgk_priemones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("svarstymo_id", sa.Integer(), nullable=False),
        sa.Column("atsakingo_id", sa.Integer(), nullable=True),
        sa.Column("aprasymas", sa.Text(), nullable=False),
        sa.Column("terminas", sa.Date(), nullable=False),
        sa.Column("busena", sa.String(length=20), nullable=False),
        sa.Column("rezultatas", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["atsakingo_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["svarstymo_id"], ["vgk_svarstymai.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vgk_priemones_atsakingo_id", "vgk_priemones", ["atsakingo_id"])
    op.create_index("ix_vgk_priemones_busena", "vgk_priemones", ["busena"])
    op.create_index("ix_vgk_priemones_svarstymo_id", "vgk_priemones", ["svarstymo_id"])
    op.create_index("ix_vgk_priemones_terminas", "vgk_priemones", ["terminas"])

    # --- Importas ---------------------------------------------------------------
    op.create_table(
        "importo_sesijos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vartotojo_id", sa.Integer(), nullable=True),
        sa.Column("failo_vardas", sa.String(length=255), nullable=False),
        sa.Column("busena", sa.String(length=20), nullable=False),
        sa.Column("eiluciu_sk", sa.Integer(), nullable=False),
        sa.Column("tinkamu_sk", sa.Integer(), nullable=False),
        sa.Column("klaidu_sk", sa.Integer(), nullable=False),
        sa.Column("sukurta", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["vartotojo_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_importo_sesijos_vartotojo_id", "importo_sesijos", ["vartotojo_id"])

    op.create_table(
        "importo_eilutes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sesijos_id", sa.Integer(), nullable=False),
        sa.Column("eilutes_nr", sa.Integer(), nullable=False),
        sa.Column("duomenys", JSON_LAUKAS, nullable=False),
        sa.Column("busena", sa.String(length=20), nullable=False),
        sa.Column("klaidos", sa.Text(), nullable=True),
        sa.Column("mokinio_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["mokinio_id"], ["mokiniai.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sesijos_id"], ["importo_sesijos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_importo_eilutes_sesijos_id", "importo_eilutes", ["sesijos_id"])

    # --- Esamos lentelės papildymas -------------------------------------------
    # VGK pareigos: NULL (ne narys), "narys", "pirmininkas" arba "sekretorius"
    op.add_column("users", sa.Column("vgk_pareigos", sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("vgk_pareigos")

    op.drop_index("ix_importo_eilutes_sesijos_id", table_name="importo_eilutes")
    op.drop_table("importo_eilutes")
    op.drop_index("ix_importo_sesijos_vartotojo_id", table_name="importo_sesijos")
    op.drop_table("importo_sesijos")

    op.drop_index("ix_vgk_priemones_terminas", table_name="vgk_priemones")
    op.drop_index("ix_vgk_priemones_svarstymo_id", table_name="vgk_priemones")
    op.drop_index("ix_vgk_priemones_busena", table_name="vgk_priemones")
    op.drop_index("ix_vgk_priemones_atsakingo_id", table_name="vgk_priemones")
    op.drop_table("vgk_priemones")
    op.drop_index("ix_vgk_dalyviai_vartotojo_id", table_name="vgk_dalyviai")
    op.drop_index("ix_vgk_dalyviai_posedzio_id", table_name="vgk_dalyviai")
    op.drop_table("vgk_dalyviai")
    op.drop_index("ix_vgk_svarstymai_posedzio_id", table_name="vgk_svarstymai")
    op.drop_index("ix_vgk_svarstymai_atvejo_id", table_name="vgk_svarstymai")
    op.drop_table("vgk_svarstymai")
    op.drop_index("ix_vgk_posedziai_data", table_name="vgk_posedziai")
    op.drop_index("ix_vgk_posedziai_busena", table_name="vgk_posedziai")
    op.drop_table("vgk_posedziai")
    op.drop_index("ix_vgk_atvejai_pateike_id", table_name="vgk_atvejai")
    op.drop_index("ix_vgk_atvejai_mokinio_id", table_name="vgk_atvejai")
    op.drop_index("ix_vgk_atvejai_busena", table_name="vgk_atvejai")
    op.drop_table("vgk_atvejai")

    op.drop_index("ix_pazymu_prasymai_tevo_id", table_name="pazymu_prasymai")
    op.drop_index("ix_pazymu_prasymai_mokinio_id", table_name="pazymu_prasymai")
    op.drop_index("ix_pazymu_prasymai_busena", table_name="pazymu_prasymai")
    op.drop_table("pazymu_prasymai")
    op.drop_table("dokumentu_skaitikliai")
    op.drop_index("ix_dokumentai_tipas", table_name="dokumentai")
    op.drop_index("ix_dokumentai_sukurta", table_name="dokumentai")
    op.drop_index("ix_dokumentai_mokinio_id", table_name="dokumentai")
    op.drop_table("dokumentai")

    op.drop_table("pranesimu_nustatymai")
    op.drop_index("ix_pranesimu_eile_taisykles_id", table_name="pranesimu_eile")
    op.drop_index("ix_pranesimu_eile_gavejo_id", table_name="pranesimu_eile")
    op.drop_index("ix_pranesimu_eile_busena_siusti_po", table_name="pranesimu_eile")
    op.drop_table("pranesimu_eile")
    op.drop_index("ix_automatizavimo_taisykles_ivykio_tipas", table_name="automatizavimo_taisykles")
    op.drop_table("automatizavimo_taisykles")
    op.drop_table("pranesimu_sablonai")
