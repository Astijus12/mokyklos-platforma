"""Production WSGI įėjimo taškas - naudojamas Gunicorn serverio.

Render.com paleidžia: gunicorn wsgi:app
"""
from app import create_app
from seed import uzpildyti_db
from models import db, User

app = create_app()

with app.app_context():
    if User.query.count() == 0:
        print("Pirmas paleidimas - užpildomi demo duomenys...")
        uzpildyti_db(naudoti_esama_app=True)
    else:
        print(f"DB jau užpildyta ({User.query.count()} vartotojai)")
