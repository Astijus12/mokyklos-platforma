"""Production WSGI įėjimo taškas - naudojamas Gunicorn serverio.

Render.com / Docker paleidžia: gunicorn wsgi:app
"""
from sqlalchemy import inspect, text

from app import create_app
from seed import uzpildyti_db
from models import db, User

app = create_app()


def _paleisti_migracijas():
    """Idempotent DB migracijos - pridedami nauji stulpeliai ir lentelės."""
    inspector = inspect(db.engine)

    def stulpelis_yra(lentele, vardas):
        try:
            return vardas in [s["name"] for s in inspector.get_columns(lentele)]
        except Exception:
            return True

    if not stulpelis_yra("users", "telefonas"):
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN telefonas VARCHAR(30)"))
        print("  + users.telefonas")

    if not stulpelis_yra("skelbimai", "matomas_tevams"):
        with db.engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE skelbimai ADD COLUMN matomas_tevams BOOLEAN NOT NULL DEFAULT FALSE"
            ))
        print("  + skelbimai.matomas_tevams")

    if not stulpelis_yra("users", "dvfa_paslaptis"):
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN dvfa_paslaptis VARCHAR(64)"))
        print("  + users.dvfa_paslaptis")

    if not stulpelis_yra("users", "dvfa_ijungtas"):
        with db.engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN dvfa_ijungtas BOOLEAN NOT NULL DEFAULT FALSE"
            ))
        print("  + users.dvfa_ijungtas")

    if not stulpelis_yra("users", "api_token_hash"):
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN api_token_hash VARCHAR(128)"))
        print("  + users.api_token_hash")

    if not stulpelis_yra("users", "api_token_data"):
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN api_token_data TIMESTAMP"))
        print("  + users.api_token_data")


with app.app_context():
    print("Paleidžiamos DB migracijos...")
    try:
        _paleisti_migracijas()
        print("[OK] Migracijos baigtos.")
    except Exception as e:
        print(f"[!] Migracijų klaida: {e}")

    if User.query.count() == 0:
        print("Pirmas paleidimas - užpildomi demo duomenys...")
        uzpildyti_db(naudoti_esama_app=True)
    else:
        print(f"DB paruošta ({User.query.count()} vartotojai)")
