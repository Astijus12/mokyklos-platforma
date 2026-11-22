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
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from models import db, EilesIrasas
from services.priminimai import PriminimuKurejas
from services.siuntejas import PranesimuSiuntejas

LAIKO_JUOSTA = "Europe/Vilnius"

zurnalas = logging.getLogger("planuokle")


def busenos_patikra():
    """Fono proceso gyvybės ženklas: į žurnalą įrašo, kiek pranešimų laukia eilėje."""
    laukia = EilesIrasas.query.filter_by(busena=EilesIrasas.LAUKIA).count()
    zurnalas.info("Fono procesas veikia. Eilėje laukia pranešimų: %s", laukia)
    return laukia


def siusti_pranesimus():
    """Kas minutę: išsiunčiama iki 20 laukiančių pranešimų (FR-A05)."""
    return PranesimuSiuntejas().siusti_partija()


def kurti_priminimus():
    """Kasdien: priminimai apie artėjančius renginius, posėdžius ir terminus (FR-A06)."""
    kiekis = PriminimuKurejas().sukurti_priminimus()
    zurnalas.info("Sukurta priminimų: %s", kiekis)
    return kiekis


def kurti_menesio_suvestine():
    """Kiekvieno mėnesio 1 d.: praėjusio mėnesio suvestinė (FR-D06)."""
    from services.pazymos import sukurti_menesio_suvestine
    dokumentas = sukurti_menesio_suvestine()
    if dokumentas is not None:
        zurnalas.info("Parengta mėnesio suvestinė %s", dokumentas.numeris)
    return dokumentas


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

    def _prideti(self, funkcija, trigeris, uzduoties_id, pavadinimas, **papildomi):
        self.planuokle.add_job(
            self._programos_kontekste(funkcija),
            trigeris,
            id=uzduoties_id,
            name=pavadinimas,
            max_instances=1,        # ta pati užduotis nevykdoma dviem egzemplioriais vienu metu
            coalesce=True,          # praleisti paleidimai sujungiami į vieną
            misfire_grace_time=60,  # pavėlavusi iki minutės užduotis vis tiek įvykdoma
            replace_existing=True,
            **papildomi,
        )

    def registruoti_uzduotis(self):
        """Užregistruoja visas fono proceso užduotis ir grąžina jų sąrašą."""
        dabar = datetime.now(ZoneInfo(LAIKO_JUOSTA))
        self._prideti(siusti_pranesimus, IntervalTrigger(minutes=1),
                      "pranesimu_siuntimas", "Pranešimų siuntimas")
        # Priminimai kasdien 7.00 ir iškart paleidus procesą: jei procesas tą rytą
        # neveikė, priminimai neprarandami (dublikatų neleidžia unikalus raktas)
        self._prideti(kurti_priminimus, CronTrigger(hour=7, minute=0, timezone=LAIKO_JUOSTA),
                      "priminimai", "Priminimų kūrimas", next_run_time=dabar)
        self._prideti(kurti_menesio_suvestine,
                      CronTrigger(day=1, hour=6, minute=0, timezone=LAIKO_JUOSTA),
                      "menesio_suvestine", "Mėnesio suvestinė")
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
