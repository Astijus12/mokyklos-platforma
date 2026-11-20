"""Fono procesas (Docker konteineris „worker“).

Paleidimas: python worker.py

1. Sukuriama ta pati Flask programa kaip žiniatinklio procese (tie patys modeliai
   ir paslaugos), tik be HTTP serverio.
2. Laukiama, kol duomenų bazėje bus įvykdytos visos migracijos – jas vykdo
   žiniatinklio procesas (wsgi.py), todėl abu procesai jų nevykdo vienu metu.
3. Užregistruojamos ir paleidžiamos planuoklės užduotys (services/planuokle.py).

Abu procesai bendrauja tik per duomenų bazę: vieno sustojimas nesugadina kito duomenų.
"""
import logging
import sys
import time

from app import create_app
from db_atnaujinimas import ar_schema_naujausia
from services.planuokle import Planuokle

zurnalas = logging.getLogger("worker")


def laukti_schemos(app, bandymu=60, pauze_s=5):
    """Laukia, kol bus pasiekiama duomenų bazė ir įvykdytos visos migracijos."""
    for bandymas in range(1, bandymu + 1):
        try:
            with app.app_context():
                if ar_schema_naujausia():
                    return True
            zurnalas.info("Laukiama, kol bus įvykdytos migracijos (%s/%s)...", bandymas, bandymu)
        except Exception as klaida:  # pvz., duomenų bazė dar nepaleista
            zurnalas.info("Duomenų bazė nepasiekiama (%s/%s): %s", bandymas, bandymu, klaida)
        time.sleep(pauze_s)
    return False


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app = create_app()

    if not laukti_schemos(app):
        zurnalas.error(
            "Duomenų bazės schema neatnaujinta. Paleiskite žiniatinklio procesą arba "
            "komandą „flask --app app atnaujinti-db“."
        )
        sys.exit(1)

    planuokle = Planuokle(app)
    planuokle.registruoti_uzduotis()
    planuokle.paleisti()


if __name__ == "__main__":
    main()
