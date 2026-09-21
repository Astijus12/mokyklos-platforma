"""Sukuria demo tėvo paskyrą ir priskiria vaikus (testavimui)."""
import sys

from app import create_app
from models import db, User, Mokinys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    app = create_app()
    with app.app_context():
        # Sukurti arba rasti demo tėvą
        email = "tevas@demo.lt"
        tevas = User.query.filter_by(email=email).first()

        if tevas is None:
            tevas = User(
                vardas="Petras",
                pavarde="Demo",
                email=email,
                telefonas="+37060000000",
                role="tevas",
            )
            tevas.nustatyti_slaptazodi("tevas123")
            db.session.add(tevas)
            db.session.commit()
            print(f"[+] Sukurta demo tevo paskyra: {email} / tevas123")
        else:
            tevas.role = "tevas"
            db.session.commit()
            print(f"[i] Rasta esama paskyra: {email}")

        # Priskirti pirmus 2 mokinius (jei yra)
        mokiniai = Mokinys.query.limit(2).all()
        if mokiniai:
            tevas.vaikai = mokiniai
            db.session.commit()
            print(f"[+] Priskirti vaikai:")
            for m in mokiniai:
                klase = m.klase.pavadinimas if m.klase else "be klases"
                print(f"    - {m.pilnas_vardas} ({klase})")
        else:
            print("[!] Sistemoje nera mokiniu, ka priskirti.")

        print()
        print("=" * 60)
        print("PRISIJUNGIMO DUOMENYS:")
        print(f"  URL:  http://127.0.0.1:5000/login")
        print(f"  Emailas: {email}")
        print(f"  Slaptazodis: tevas123")
        print("=" * 60)


if __name__ == "__main__":
    main()
