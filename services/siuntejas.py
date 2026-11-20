"""Pranešimų siuntėjas (aprašo 6 pav. klasė PranesimuSiuntejas).

Fono procesas kas minutę kviečia siusti_partija(): paimami iki 20 laukiančių
įrašų ir kiekvienas išsiunčiamas per atitinkamą kanalą. Nepavykus siuntimas
kartojamas vėliau, o po paskutinio bandymo informuojami administratoriai (FR-A05).
"""
import logging

from models import EilesIrasas, Pranesimas, User, db
from services.eile import PranesimuEile
from services.ivykiai import kelias
from services.kanalai import ElPastoKanalas, SistemosKanalas, SiuntimoKlaida

zurnalas = logging.getLogger("siuntejas")

PARTIJOS_DYDIS = 20


class PranesimuSiuntejas:
    """Siunčia eilės įrašus per kanalus (el. paštas, sistemos pranešimų centras)."""

    def __init__(self, eile=None, kanalai=None):
        self.eile = eile or PranesimuEile()
        kanalai = kanalai if kanalai is not None else [ElPastoKanalas(), SistemosKanalas()]
        self.kanalai = {kanalas.kodas: kanalas for kanalas in kanalai}

    def siusti_partija(self, kiekis=PARTIJOS_DYDIS):
        """Išsiunčia vieną partiją ir grąžina sėkmingai išsiųstų pranešimų skaičių."""
        grazinta = self.eile.grazinti_uzstrigusius()
        if grazinta:
            zurnalas.warning("Į eilę grąžinta užstrigusių įrašų: %s", grazinta)

        issiusta = 0
        for irasas in self.eile.paimti_laukiancius(kiekis):
            if self._siusti_viena(irasas):
                issiusta += 1
        if issiusta:
            zurnalas.info("Išsiųsta pranešimų: %s", issiusta)
        return issiusta

    def _siusti_viena(self, irasas):
        kanalas = self.kanalai.get(irasas.kanalas)
        try:
            if kanalas is None:
                raise SiuntimoKlaida(f"Nežinomas kanalas: {irasas.kanalas}")
            kanalas.siusti(irasas)
        except Exception as klaida:  # bet kokia kanalo klaida – bandymas nepavyko
            db.session.rollback()
            # Po rollback objektas pakartotinai užkraunamas iš duomenų bazės
            irasas = db.session.get(EilesIrasas, irasas.id)
            self.eile.atideti(irasas, str(klaida))
            zurnalas.warning("Pranešimo %s išsiųsti nepavyko (%s bandymas): %s",
                             irasas.id, irasas.bandymai, klaida)
            if irasas.busena == EilesIrasas.NEPAVYKO:
                self._informuoti_administratorius(irasas)
            return False

        self.eile.pazymeti_issiusta(irasas)
        return True

    def _informuoti_administratorius(self, irasas):
        """Galutinai nepavykęs pranešimas – įspėjimas administratoriams pranešimų centre.

        Įspėjimas kuriamas tiesiogiai (ne per eilę), kad nepavykęs el. paštas
        nesukeltų naujų nepavykusių laiškų.
        """
        gavejas = irasas.gavejas.pilnas_vardas if irasas.gavejas else "nežinomas gavėjas"
        for admin in User.query.filter_by(role="administratorius").all():
            db.session.add(Pranesimas(
                vartotojo_id=admin.id,
                pavadinimas="Pranešimo išsiųsti nepavyko",
                tekstas=f"„{irasas.tema}“ ({gavejas}) neišsiųstas po {irasas.bandymai} bandymų. "
                        f"Klaida: {irasas.klaida}",
                nuoroda=kelias("automatizavimas.zurnalas", busena=EilesIrasas.NEPAVYKO),
                ikona="alert-triangle",
                tipas="klaida",
            ))
        db.session.commit()
