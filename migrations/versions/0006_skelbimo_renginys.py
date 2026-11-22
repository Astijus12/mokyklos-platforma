"""Skelbimo renginys kalendoriuje: renginiai.skelbimo_id.

Skelbime nurodžius renginio datą, sukuriamas susietas renginys, kuris rodomas
mokyklos kalendoriuje. Pašalinus skelbimą, pašalinamas ir jo renginys.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-22 23:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("renginiai") as lentele:
        lentele.add_column(sa.Column("skelbimo_id", sa.Integer(), nullable=True))
        lentele.create_foreign_key("fk_renginiai_skelbimo_id_skelbimai", "skelbimai",
                                   ["skelbimo_id"], ["id"], ondelete="CASCADE")
        lentele.create_unique_constraint("uq_renginiai_skelbimo_id", ["skelbimo_id"])


def downgrade():
    with op.batch_alter_table("renginiai") as lentele:
        lentele.drop_constraint("uq_renginiai_skelbimo_id", type_="unique")
        lentele.drop_constraint("fk_renginiai_skelbimo_id_skelbimai", type_="foreignkey")
        lentele.drop_column("skelbimo_id")
