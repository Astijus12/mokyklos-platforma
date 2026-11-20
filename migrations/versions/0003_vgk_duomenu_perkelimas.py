"""VGK duomenų perkėlimas: mokiniai.geroves_* -> vgk_atvejai.

Iki baigiamojo darbo mokinio kortelėje buvo tik žymė „svarstytas Vaiko gerovės
komisijoje“ (geroves_komisija), data ir pastabos. Ši migracija kiekvienam
mokiniui su tokiais duomenimis sukuria įrašą lentelėje vgk_atvejai ir pašalina
tris senus stulpelius:

- pažymėta žymė -> atvejis būsenoje „Svarstomas“ (mokinys jau svarstytas);
- nepažymėta, bet yra data ar pastabos -> „Užbaigtas“ atvejis (istorija);
- data -> atvejo sukūrimo laikas (jei datos nėra – migracijos laikas);
- pastabos -> kreipimosi priežastis.

Esami puslapiai toliau veikia, nes modelis Mokinys turi savybes tais pačiais
vardais (geroves_komisija ir kt.), kurios skaito iš vgk_atvejai.

Migraciją galima saugiai kartoti: mokiniui, kuris jau turi VGK atvejį, naujas
nekuriamas. Atšaukimas (downgrade) grąžina stulpelius ir į juos nukopijuoja
naujausio neužbaigto atvejo duomenis; atvejų lentelės neliečia.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-20 19:10:00
"""
from datetime import datetime, time, timezone

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# Lentelių aprašai tik šiai migracijai. Programos modeliai (models/) čia
# nenaudojami, nes jie ateityje keisis, o migracija turi veikti visada vienodai.
mokiniai = sa.table(
    "mokiniai",
    sa.column("id", sa.Integer),
    sa.column("geroves_komisija", sa.Boolean),
    sa.column("geroves_komisija_data", sa.Date),
    sa.column("geroves_komisija_pastabos", sa.Text),
)
vgk_atvejai = sa.table(
    "vgk_atvejai",
    sa.column("id", sa.Integer),
    sa.column("mokinio_id", sa.Integer),
    sa.column("pateike_id", sa.Integer),
    sa.column("priezastis", sa.Text),
    sa.column("busena", sa.String),
    sa.column("sukurta", sa.DateTime),
    sa.column("uzbaigta", sa.DateTime),
)

NUMATYTOJI_PRIEZASTIS = "Perkelta iš mokinio kortelės (ankstesnė sistemos versija)."


def upgrade():
    rysys = op.get_bind()
    dabar = datetime.now(timezone.utc).replace(tzinfo=None)

    jau_turi_atveji = {
        eil.mokinio_id for eil in rysys.execute(sa.select(vgk_atvejai.c.mokinio_id))
    }

    su_vgk_duomenimis = rysys.execute(
        sa.select(mokiniai).where(
            sa.or_(
                mokiniai.c.geroves_komisija == sa.true(),
                mokiniai.c.geroves_komisija_data.isnot(None),
                mokiniai.c.geroves_komisija_pastabos.isnot(None),
            )
        )
    ).fetchall()

    nauji_atvejai = []
    for m in su_vgk_duomenimis:
        if m.id in jau_turi_atveji:
            continue
        aktyvus = bool(m.geroves_komisija)
        if m.geroves_komisija_data:
            sukurta = datetime.combine(m.geroves_komisija_data, time())
        else:
            sukurta = dabar
        nauji_atvejai.append({
            "mokinio_id": m.id,
            "pateike_id": None,  # senoje versijoje nebuvo saugoma, kas pažymėjo
            "priezastis": (m.geroves_komisija_pastabos or "").strip() or NUMATYTOJI_PRIEZASTIS,
            "busena": "svarstomas" if aktyvus else "uzbaigtas",
            "sukurta": sukurta,
            "uzbaigta": None if aktyvus else sukurta,
        })

    if nauji_atvejai:
        op.bulk_insert(vgk_atvejai, nauji_atvejai)

    # SQLite stulpelius šalina perkurdama lentelę, todėl naudojamas „batch“ režimas
    with op.batch_alter_table("mokiniai") as batch_op:
        batch_op.drop_column("geroves_komisija_pastabos")
        batch_op.drop_column("geroves_komisija_data")
        batch_op.drop_column("geroves_komisija")


def downgrade():
    with op.batch_alter_table("mokiniai") as batch_op:
        batch_op.add_column(
            sa.Column("geroves_komisija", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("geroves_komisija_data", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("geroves_komisija_pastabos", sa.Text(), nullable=True))

    rysys = op.get_bind()
    aktyvus_atvejai = rysys.execute(
        sa.select(vgk_atvejai)
        .where(vgk_atvejai.c.busena != "uzbaigtas")
        .order_by(vgk_atvejai.c.sukurta)
    ).fetchall()

    # Kiekvienam mokiniui lieka naujausias neužbaigtas atvejis (vėlesnis perrašo ankstesnį)
    naujausias = {a.mokinio_id: a for a in aktyvus_atvejai}
    for mokinio_id, atvejis in naujausias.items():
        rysys.execute(
            mokiniai.update()
            .where(mokiniai.c.id == mokinio_id)
            .values(
                geroves_komisija=True,
                geroves_komisija_data=atvejis.sukurta.date(),
                geroves_komisija_pastabos=atvejis.priezastis,
            )
        )
