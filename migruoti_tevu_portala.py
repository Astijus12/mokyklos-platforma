"""Migracija: prideda tėvų portalo lenteles ir laukus.

Prideda:
- users.telefonas stulpelį (jei jo nėra)
- tevu_vaiku_rysys asociacijos lentelę

Saugu paleisti kelis kartus - patikrina, ar objektai jau egzistuoja.
"""
import sys
from sqlalchemy import inspect, text

from app import create_app
from models import db

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def stulpelis_egzistuoja(inspector, lentele, stulpelio_vardas):
    stulpeliai = [s["name"] for s in inspector.get_columns(lentele)]
    return stulpelio_vardas in stulpeliai


def lentele_egzistuoja(inspector, lenteles_vardas):
    return lenteles_vardas in inspector.get_table_names()


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        pakeitimai = 0

        # 1. users.telefonas stulpelis
        if not stulpelis_egzistuoja(inspector, "users", "telefonas"):
            print("+ Pridedamas users.telefonas stulpelis...")
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN telefonas VARCHAR(30)"))
            pakeitimai += 1
        else:
            print("- users.telefonas jau yra, praleidžiama.")

        # 2. tevu_vaiku_rysys lentelė
        if not lentele_egzistuoja(inspector, "tevu_vaiku_rysys"):
            print("+ Kuriama tevu_vaiku_rysys lentelė...")
            db.create_all()
            pakeitimai += 1
        else:
            print("- tevu_vaiku_rysys jau egzistuoja, praleidžiama.")

        # 3. skelbimai.matomas_tevams stulpelis
        if not stulpelis_egzistuoja(inspector, "skelbimai", "matomas_tevams"):
            print("+ Pridedamas skelbimai.matomas_tevams stulpelis...")
            with db.engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE skelbimai ADD COLUMN matomas_tevams BOOLEAN NOT NULL DEFAULT 0"
                ))
            pakeitimai += 1
        else:
            print("- skelbimai.matomas_tevams jau yra, praleidžiama.")

        # 4. users.dvfa_paslaptis ir users.dvfa_ijungtas stulpeliai (2FA)
        if not stulpelis_egzistuoja(inspector, "users", "dvfa_paslaptis"):
            print("+ Pridedamas users.dvfa_paslaptis stulpelis...")
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN dvfa_paslaptis VARCHAR(64)"))
            pakeitimai += 1
        else:
            print("- users.dvfa_paslaptis jau yra, praleidžiama.")

        if not stulpelis_egzistuoja(inspector, "users", "dvfa_ijungtas"):
            print("+ Pridedamas users.dvfa_ijungtas stulpelis...")
            with db.engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN dvfa_ijungtas BOOLEAN NOT NULL DEFAULT 0"
                ))
            pakeitimai += 1
        else:
            print("- users.dvfa_ijungtas jau yra, praleidžiama.")

        # 5. users.api_token_hash ir users.api_token_data (REST API)
        if not stulpelis_egzistuoja(inspector, "users", "api_token_hash"):
            print("+ Pridedamas users.api_token_hash stulpelis...")
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN api_token_hash VARCHAR(128)"))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_users_api_token_hash ON users (api_token_hash)"
                ))
            pakeitimai += 1
        else:
            print("- users.api_token_hash jau yra, praleidžiama.")

        if not stulpelis_egzistuoja(inspector, "users", "api_token_data"):
            print("+ Pridedamas users.api_token_data stulpelis...")
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN api_token_data DATETIME"))
            pakeitimai += 1
        else:
            print("- users.api_token_data jau yra, praleidžiama.")

        # 6. skelbimai.kategorija
        if not stulpelis_egzistuoja(inspector, "skelbimai", "kategorija"):
            print("+ Pridedamas skelbimai.kategorija stulpelis...")
            with db.engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE skelbimai ADD COLUMN kategorija VARCHAR(30) NOT NULL DEFAULT 'bendra'"
                ))
            pakeitimai += 1
        else:
            print("- skelbimai.kategorija jau yra, praleidžiama.")

        # 7. mokiniai.nuotraukos_failas
        if not stulpelis_egzistuoja(inspector, "mokiniai", "nuotraukos_failas"):
            print("+ Pridedamas mokiniai.nuotraukos_failas stulpelis...")
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE mokiniai ADD COLUMN nuotraukos_failas VARCHAR(300)"))
            pakeitimai += 1
        else:
            print("- mokiniai.nuotraukos_failas jau yra, praleidžiama.")

        # 8. Naujos lentelės (renginiai, veiklos_zurnalas, pranesimai)
        for lenteles_vardas in ["renginiai", "veiklos_zurnalas", "pranesimai"]:
            if not lentele_egzistuoja(inspector, lenteles_vardas):
                print(f"+ Kuriama {lenteles_vardas} lentelė...")
                db.create_all()
                pakeitimai += 1
                break  # visos sukurtos vienu iškvietimu
        else:
            print("- naujos lentelės jau egzistuoja, praleidžiama.")

        print()
        print("=" * 60)
        if pakeitimai > 0:
            print(f"[OK] Atlikta {pakeitimai} migracijos pakeitimai.")
        else:
            print("[OK] DB jau atnaujinta, nieko keisti nereikia.")
        print("=" * 60)


if __name__ == "__main__":
    main()
