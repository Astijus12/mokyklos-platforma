"""Pranešimų kanalai (aprašo 6 pav. sąsaja Kanalas ir jos realizacijos).

PranesimuSiuntejas siunčia pranešimus tik per sąsają Kanalas, todėl naują kanalą
(pvz., SMS) galima pridėti nekeičiant kitų klasių.
"""
import os
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from flask import current_app

from models import Pranesimas, db, utc_dabar


class SiuntimoKlaida(Exception):
    """Pranešimo išsiųsti nepavyko (pvz., el. pašto serveris nepasiekiamas)."""


class Kanalas(ABC):
    """Kanalo sąsaja: siusti() grąžina True arba, nepavykus, kelia SiuntimoKlaida."""

    kodas = None
    pavadinimas = None

    @abstractmethod
    def siusti(self, irasas):
        """Išsiunčia vieną eilės įrašą."""

    def uzdaryti(self):
        """Atlaisvina kanalo išteklius baigus siųsti (pagal nutylėjimą nieko nedaro)."""


class ElPastoKanalas(Kanalas):
    """El. laiškai per SMTP serverį (smtplib).

    Kūrimo aplinkoje be SMTP serverio (MAIL_BACKEND=failai) laiškai neišsiunčiami,
    o įrašomi kaip .eml failai į katalogą MAIL_FAILU_KATALOGAS – juos galima
    atidaryti pašto programa ir patikrinti turinį.

    Viena SMTP jungtis naudojama visiems vieno siuntimo paleidimo laiškams:
    prisijungimas (TLS, slaptažodis) užtrunka ilgiau nei pats laiško išsiuntimas (NFR-03).
    Jungtį uždaro uzdaryti(), kurį kviečia PranesimuSiuntejas.
    """

    kodas = "el_pastas"
    pavadinimas = "El. paštas"

    def __init__(self, nustatymai=None):
        self._nustatymai = nustatymai
        self._smtp = None  # atvira jungtis; None – dar neprisijungta

    def _konf(self, raktas, numatytoji=None):
        saltinis = self._nustatymai if self._nustatymai is not None else current_app.config
        return saltinis.get(raktas, numatytoji)

    def sukurti_laiska(self, irasas):
        siuntejas = self._konf("MAIL_SENDER") or "noreply@mokykla.lt"
        laiskas = EmailMessage()
        laiskas["Subject"] = irasas.tema
        laiskas["From"] = siuntejas
        laiskas["To"] = irasas.gavejas.email
        laiskas["Date"] = formatdate(localtime=True)
        laiskas["Message-ID"] = make_msgid(domain=siuntejas.rsplit("@", 1)[-1].strip(">"))
        laiskas["Auto-Submitted"] = "auto-generated"  # automatinis laiškas, atsakymų nereikia
        laiskas.set_content(irasas.tekstas)
        return laiskas

    def _irasyti_faila(self, irasas, laiskas):
        katalogas = self._konf("MAIL_FAILU_KATALOGAS")
        os.makedirs(katalogas, exist_ok=True)
        pavadinimas = f"{utc_dabar():%Y%m%d_%H%M%S}_irasas_{irasas.id}.eml"
        with open(os.path.join(katalogas, pavadinimas), "wb") as failas:
            failas.write(bytes(laiskas))

    def _prisijungti(self):
        """Atidaro SMTP jungtį: TLS ir prisijungimas, jei jie nurodyti nustatymuose."""
        serveris = self._konf("MAIL_SERVER")
        if not serveris:
            raise SiuntimoKlaida("Nenurodytas el. pašto serveris (MAIL_SERVER).")

        jungtis = smtplib.SMTP_SSL if self._konf("MAIL_USE_SSL") else smtplib.SMTP
        smtp = jungtis(serveris, int(self._konf("MAIL_PORT", 587)),
                       timeout=int(self._konf("MAIL_TIMEOUT", 15)))
        try:
            if self._konf("MAIL_USE_TLS") and not self._konf("MAIL_USE_SSL"):
                smtp.starttls()
            if self._konf("MAIL_USERNAME"):
                smtp.login(self._konf("MAIL_USERNAME"), self._konf("MAIL_PASSWORD") or "")
        except BaseException:
            smtp.close()
            raise
        return smtp

    def siusti(self, irasas):
        laiskas = self.sukurti_laiska(irasas)

        if self._konf("MAIL_BACKEND", "smtp") == "failai":
            self._irasyti_faila(irasas, laiskas)
            return True

        try:
            if self._smtp is None:
                self._smtp = self._prisijungti()
            self._smtp.send_message(laiskas)
        except (smtplib.SMTPException, OSError) as klaida:
            # Sugedusi jungtis nebenaudojama – kitas laiškas prisijungs iš naujo
            self.uzdaryti()
            raise SiuntimoKlaida(f"El. laiško išsiųsti nepavyko: {klaida}") from klaida
        return True

    def uzdaryti(self):
        """Uždaro SMTP jungtį (jei ji atidaryta)."""
        if self._smtp is None:
            return
        try:
            self._smtp.quit()
        except (smtplib.SMTPException, OSError):
            self._smtp.close()
        self._smtp = None


# Pranešimų centro ikonos pagal įvykio tipo pradžią (Lucide ikonų pavadinimai)
_IKONOS = (
    ("skelbimas", "megaphone"),
    ("renginys", "calendar"),
    ("vgk", "heart-handshake"),
    ("priemon", "list-checks"),
    ("pazymos", "file-text"),
    ("importas", "file-up"),
    ("menesio", "bar-chart-3"),
)


class SistemosKanalas(Kanalas):
    """Sistemos pranešimų centras (varpelio ikona) – esamas modelis Pranesimas."""

    kodas = "sistema"
    pavadinimas = "Sistema"

    @staticmethod
    def ikona(irasas):
        tipas = irasas.taisykle.ivykio_tipas if irasas.taisykle is not None else ""
        for pradzia, ikona in _IKONOS:
            if tipas.startswith(pradzia):
                return ikona
        return "bell"

    def siusti(self, irasas):
        # Pranešimas išsaugomas kartu su eilės įrašo būsena (PranesimuEile.pazymeti_issiusta)
        db.session.add(Pranesimas(
            vartotojo_id=irasas.gavejo_id,
            pavadinimas=irasas.tema[:200],
            tekstas=irasas.tekstas,
            ikona=self.ikona(irasas),
            tipas="info",
        ))
        return True
