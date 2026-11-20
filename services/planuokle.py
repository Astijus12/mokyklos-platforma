"""Planuoklė – fono proceso periodinės užduotys (APScheduler 3.11).

Klasė Planuokle (aprašo 6 pav. „Paslaugų sluoksnio klasių diagrama“) užregistruoja
užduotis ir paleidžia planuoklę. Ją naudoja tik fono procesas (worker.py):
jei planuoklė veiktų žiniatinklio procese, o Gunicorn paleistų kelis darbinius
procesus, kiekviena užduotis būtų vykdoma kelis kartus.

Kiekviena užduotis vykdoma Flask programos kontekste, todėl gali naudoti
modelius ir paslaugas. Užduoties klaida užrašoma į žurnalą ir nesustabdo
planuoklės – kitos užduotys vykdomos toliau.
"""
import logging
from functools import wraps

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from models import db, EilesIrasas

LAIKO_JUOSTA = "Europe/Vilnius"

zurnalas = logging.getLogger("planuokle")


def busenos_patikra():
    """Fono proceso gyvybės ženklas: į žurnalą įrašo, kiek pranešimų laukia eilėje."""
    laukia = EilesIrasas.query.filter_by(busena=EilesIrasas.LAUKIA).count()
    zurnalas.info("Fono procesas veikia. Eilėje laukia pranešimų: %s", laukia)
    return laukia


class Planuokle:
    """Registruoja ir paleidžia periodines užduotis."""

    def __init__(self, app, planuokle=None):
        self.app = app
        # Testuose galima perduoti kitą planuoklę (pvz., BackgroundScheduler)
        self.planuokle = planuokle or BlockingScheduler(timezone=LAIKO_JUOSTA)

    def _programos_kontekste(self, funkcija):
        """Apgaubia užduotį: programos kontekstas, klaidų žurnalas, sesijos uždarymas."""
        @wraps(funkcija)
        def vykdyti():
            with self.app.app_context():
                try:
                    return funkcija()
                except Exception:
                    db.session.rollback()
                    zurnalas.exception("Užduotis „%s“ nepavyko", funkcija.__name__)
                    return None
                finally:
                    db.session.remove()
        return vykdyti

    def _prideti(self, funkcija, trigeris, uzduoties_id, pavadinimas):
        self.planuokle.add_job(
            self._programos_kontekste(funkcija),
            trigeris,
            id=uzduoties_id,
            name=pavadinimas,
            max_instances=1,        # ta pati užduotis nevykdoma dviem egzemplioriais vienu metu
            coalesce=True,          # praleisti paleidimai sujungiami į vieną
            misfire_grace_time=60,  # pavėlavusi iki minutės užduotis vis tiek įvykdoma
            replace_existing=True,
        )

    def registruoti_uzduotis(self):
        """Užregistruoja visas fono proceso užduotis ir grąžina jų sąrašą."""
        self._prideti(busenos_patikra, IntervalTrigger(minutes=15),
                      "busenos_patikra", "Fono proceso būsenos patikra")
        return self.planuokle.get_jobs()

    def paleisti(self):
        """Paleidžia planuoklę (BlockingScheduler blokuoja, kol procesas sustabdomas)."""
        pavadinimai = ", ".join(u.name for u in self.planuokle.get_jobs())
        zurnalas.info("Planuoklė paleidžiama. Užduotys: %s", pavadinimai)
        try:
            self.planuokle.start()
        except (KeyboardInterrupt, SystemExit):
            zurnalas.info("Planuoklė sustabdyta.")
