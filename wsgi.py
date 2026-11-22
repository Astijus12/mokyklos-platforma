"""Production WSGI įėjimo taškas - naudojamas Gunicorn serverio.

Render.com / Docker paleidžia: gunicorn --preload wsgi:app

Paleidžiant atnaujinama duomenų bazės schema (Alembic migracijos, žr.
db_atnaujinimas.py), o tuščia duomenų bazė užpildoma demonstraciniais duomenimis.
Su --preload šis failas įvykdomas vieną kartą pagrindiniame Gunicorn procese,
todėl migracijos nevykdomos lygiagrečiai keliuose darbiniuose procesuose.
"""
import threading

from app import create_app
from db_atnaujinimas import atnaujinti_duomenu_baze
from models import db, User
from seed import uzpildyti_db
from services.planuokle import ar_paleisti_web_procese, paleisti_fone

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


# Render nemokamame plane fono proceso (worker.py) nėra, todėl planuoklė paleidžiama
# darbiniame Gunicorn procese per pirmą užklausą. Ne aukščiau, pagrindiniame procese:
# su --preload jis vėliau išsišakoja (fork), o gijos į darbinius procesus nepatenka.
if ar_paleisti_web_procese():
    _planuokle = []
    _planuokles_uzraktas = threading.Lock()

    @app.before_request
    def _paleisti_planuokle():
        if not _planuokle:
            with _planuokles_uzraktas:
                if not _planuokle:
                    _planuokle.append(paleisti_fone(app))
