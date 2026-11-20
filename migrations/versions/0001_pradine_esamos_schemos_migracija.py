"""Pradinė esamos schemos migracija (praktikų metu sukurtos 9 lentelės).

Ši migracija aprašo duomenų bazę tokią, kokia ji buvo prieš baigiamąjį darbą:
users, klases, mokiniai, tevu_vaiku_rysys, diplomai, skelbimai, renginiai,
veiklos_zurnalas ir pranesimai. Naujoje (tuščioje) duomenų bazėje ji sukuria
šias lenteles, o senoje, sukurtoje be Alembic, ji nevykdoma – tokia duomenų
bazė tik pažymima šia versija (žr. db_atnaujinimas.py).

Revision ID: 0001
Revises:
Create Date: 2026-11-20 18:55:09
"""
from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vardas", sa.String(length=80), nullable=False),
        sa.Column("pavarde", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("telefonas", sa.String(length=30), nullable=True),
        sa.Column("slaptazodzio_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("sukurtas", sa.DateTime(), nullable=True),
        sa.Column("dvfa_paslaptis", sa.String(length=64), nullable=True),
        sa.Column("dvfa_ijungtas", sa.Boolean(), nullable=False),
        sa.Column("api_token_hash", sa.String(length=128), nullable=True),
        sa.Column("api_token_data", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_api_token_hash", "users", ["api_token_hash"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "diplomai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pavadinimas", sa.String(length=200), nullable=False),
        sa.Column("aprasymas", sa.Text(), nullable=True),
        sa.Column("seminaras", sa.String(length=200), nullable=True),
        sa.Column("isdavimo_data", sa.Date(), nullable=True),
        sa.Column("failo_kelias", sa.String(length=300), nullable=False),
        sa.Column("originalus_failo_vardas", sa.String(length=300), nullable=False),
        sa.Column("failo_tipas", sa.String(length=20), nullable=False),
        sa.Column("vartotojo_id", sa.Integer(), nullable=False),
        sa.Column("ikeltas", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vartotojo_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "klases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pavadinimas", sa.String(length=20), nullable=False),
        sa.Column("mokslo_metai", sa.String(length=20), nullable=False),
        sa.Column("vadovo_id", sa.Integer(), nullable=True),
        sa.Column("sukurtas", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vadovo_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pavadinimas"),
    )

    op.create_table(
        "pranesimai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vartotojo_id", sa.Integer(), nullable=False),
        sa.Column("pavadinimas", sa.String(length=200), nullable=False),
        sa.Column("tekstas", sa.Text(), nullable=True),
        sa.Column("nuoroda", sa.String(length=300), nullable=True),
        sa.Column("ikona", sa.String(length=30), nullable=False),
        sa.Column("tipas", sa.String(length=20), nullable=False),
        sa.Column("perskaitytas", sa.Boolean(), nullable=False),
        sa.Column("sukurtas", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vartotojo_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pranesimai_perskaitytas", "pranesimai", ["perskaitytas"], unique=False)
    op.create_index("ix_pranesimai_sukurtas", "pranesimai", ["sukurtas"], unique=False)
    op.create_index("ix_pranesimai_vartotojo_id", "pranesimai", ["vartotojo_id"], unique=False)

    op.create_table(
        "renginiai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pavadinimas", sa.String(length=200), nullable=False),
        sa.Column("aprasymas", sa.Text(), nullable=True),
        sa.Column("pradzios_data", sa.Date(), nullable=False),
        sa.Column("pradzios_laikas", sa.Time(), nullable=True),
        sa.Column("pabaigos_data", sa.Date(), nullable=True),
        sa.Column("pabaigos_laikas", sa.Time(), nullable=True),
        sa.Column("vieta", sa.String(length=200), nullable=True),
        sa.Column("kategorija", sa.String(length=30), nullable=False),
        sa.Column("matomas_tevams", sa.Boolean(), nullable=False),
        sa.Column("vartotojo_id", sa.Integer(), nullable=False),
        sa.Column("sukurtas", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vartotojo_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_renginiai_pradzios_data", "renginiai", ["pradzios_data"], unique=False)

    op.create_table(
        "skelbimai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pavadinimas", sa.String(length=200), nullable=False),
        sa.Column("turinys", sa.Text(), nullable=False),
        sa.Column("svarbus", sa.Boolean(), nullable=True),
        sa.Column("matomas_tevams", sa.Boolean(), nullable=False),
        sa.Column("kategorija", sa.String(length=30), nullable=False),
        sa.Column("vartotojo_id", sa.Integer(), nullable=False),
        sa.Column("sukurtas", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vartotojo_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "veiklos_zurnalas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vartotojo_id", sa.Integer(), nullable=True),
        sa.Column("veiksmas", sa.String(length=50), nullable=False),
        sa.Column("objekto_tipas", sa.String(length=50), nullable=True),
        sa.Column("objekto_id", sa.Integer(), nullable=True),
        sa.Column("aprasymas", sa.String(length=500), nullable=True),
        sa.Column("ip_adresas", sa.String(length=50), nullable=True),
        sa.Column("laikas", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vartotojo_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_veiklos_zurnalas_laikas", "veiklos_zurnalas", ["laikas"], unique=False)
    op.create_index("ix_veiklos_zurnalas_vartotojo_id", "veiklos_zurnalas", ["vartotojo_id"], unique=False)
    op.create_index("ix_veiklos_zurnalas_veiksmas", "veiklos_zurnalas", ["veiksmas"], unique=False)

    op.create_table(
        "mokiniai",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vardas", sa.String(length=80), nullable=False),
        sa.Column("pavarde", sa.String(length=80), nullable=False),
        sa.Column("gimimo_data", sa.Date(), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("telefonas", sa.String(length=30), nullable=True),
        sa.Column("adresas", sa.String(length=200), nullable=True),
        sa.Column("pastabos", sa.Text(), nullable=True),
        sa.Column("klases_id", sa.Integer(), nullable=False),
        sa.Column("sukurtas", sa.DateTime(), nullable=True),
        sa.Column("motinos_vardas", sa.String(length=160), nullable=True),
        sa.Column("motinos_telefonas", sa.String(length=30), nullable=True),
        sa.Column("motinos_email", sa.String(length=120), nullable=True),
        sa.Column("tevo_vardas", sa.String(length=160), nullable=True),
        sa.Column("tevo_telefonas", sa.String(length=30), nullable=True),
        sa.Column("tevo_email", sa.String(length=120), nullable=True),
        sa.Column("mokyklos_autobusas", sa.Boolean(), nullable=False),
        # Šie trys laukai migracijoje 0003 perkeliami į vgk_atvejai ir pašalinami
        sa.Column("geroves_komisija", sa.Boolean(), nullable=False),
        sa.Column("geroves_komisija_data", sa.Date(), nullable=True),
        sa.Column("geroves_komisija_pastabos", sa.Text(), nullable=True),
        sa.Column("nuotraukos_failas", sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(["klases_id"], ["klases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tevu_vaiku_rysys",
        sa.Column("tevo_id", sa.Integer(), nullable=False),
        sa.Column("vaiko_id", sa.Integer(), nullable=False),
        sa.Column("rysio_tipas", sa.String(length=20), nullable=False),
        sa.Column("sukurtas", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tevo_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vaiko_id"], ["mokiniai.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tevo_id", "vaiko_id"),
    )


def downgrade():
    op.drop_table("tevu_vaiku_rysys")
    op.drop_table("mokiniai")
    op.drop_index("ix_veiklos_zurnalas_veiksmas", table_name="veiklos_zurnalas")
    op.drop_index("ix_veiklos_zurnalas_vartotojo_id", table_name="veiklos_zurnalas")
    op.drop_index("ix_veiklos_zurnalas_laikas", table_name="veiklos_zurnalas")
    op.drop_table("veiklos_zurnalas")
    op.drop_table("skelbimai")
    op.drop_index("ix_renginiai_pradzios_data", table_name="renginiai")
    op.drop_table("renginiai")
    op.drop_index("ix_pranesimai_vartotojo_id", table_name="pranesimai")
    op.drop_index("ix_pranesimai_sukurtas", table_name="pranesimai")
    op.drop_index("ix_pranesimai_perskaitytas", table_name="pranesimai")
    op.drop_table("pranesimai")
    op.drop_table("klases")
    op.drop_table("diplomai")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_api_token_hash", table_name="users")
    op.drop_table("users")
