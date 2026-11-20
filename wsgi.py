"""Production WSGI įėjimo taškas - naudojamas Gunicorn serverio.

Render.com / Docker paleidžia: gunicorn --preload wsgi:app

Paleidžiant atnaujinama duomenų bazės schema (Alembic migracijos, žr.
db_atnaujinimas.py), o tuščia duomenų bazė užpildoma demonstraciniais duomenimis.
Su --preload šis failas įvykdomas vieną kartą pagrindiniame Gunicorn procese,
todėl migracijos nevykdomos lygiagrečiai keliuose darbiniuose procesuose.
"""
from app import create_app
from db_atnaujinimas import atnaujinti_duomenu_baze
from models import db, User
from seed import uzpildyti_db

app = create_app()

with app.app_context():
    print("Atnaujinama duomenų bazės schema (migracijos)...")
    atnaujinti_duomenu_baze()
    print("[OK] Schema atnaujinta.")

    if User.query.count() == 0:
        print("Pirmas paleidimas - užpildomi demo duomenys...")
        uzpildyti_db(naudoti_esama_app=True, isvalyti=False)
    else:
        print(f"DB paruošta ({User.query.count()} vartotojai)")

    # Prisijungimai uždaromi prieš Gunicorn sukuriant darbinius procesus:
    # kiekvienas procesas turi atsidaryti savo prisijungimus prie duomenų bazės.
    db.session.remove()
    db.engine.dispose()
