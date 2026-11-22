"""Pranešimų siuntėjas (aprašo 6 pav. klasė PranesimuSiuntejas).

Fono procesas kas minutę kviečia siusti_eile(): iš eilės paimama partija – iki
20 laukiančių įrašų – ir kiekvienas išsiunčiamas per atitinkamą kanalą. Partijos
imamos viena po kitos, kol eilė ištuštėja arba baigiasi laiko riba (50 s), todėl
ir 200 įrašų eilė išsiunčiama per vieną paleidimą (NFR-03). Nepavykus siuntimas
kartojamas vėliau, o po paskutinio bandymo informuojami administratoriai (FR-A05).
"""
import logging
import time

from models import EilesIrasas, Pranesimas, User, db
from services.eile import PranesimuEile
from services.ivykiai import kelias
from services.kanalai import ElPastoKanalas, SistemosKanalas, SiuntimoKlaida

zurnalas = logging.getLogger("siuntejas")

# Tiek įrašų vienu metu užrakinama duomenų bazėje (SELECT ... FOR UPDATE SKIP LOCKED)
PARTIJOS_DYDIS = 20
# Vienas paleidimas baigiamas iki kito (fono procesas siuntėją kviečia kas minutę)
LAIKO_RIBA_S = 50


class PranesimuSiuntejas:
    """Siunčia eilės įrašus per kanalus (el. paštas, sistemos pranešimų centras)."""

    def __init__(self, eile=None, kanalai=None):
        self.eile = eile or PranesimuEile()
        kanalai = kanalai if kanalai is not None else [ElPastoKanalas(), SistemosKanalas()]
        self.kanalai = {kanalas.kodas: kanalas for kanalas in kanalai}

    def siusti_eile(self, kiekis=PARTIJOS_DYDIS, laiko_riba=LAIKO_RIBA_S):
        """Siunčia partijomis, kol eilė ištuštėja arba baigiasi laiko riba.

        Grąžina sėkmingai išsiųstų pranešimų skaičių. Nepavykę įrašai atidedami
        vėlesniam laikui, todėl tame pačiame paleidime antrą kartą nepaimami.
        """
        pradzia = time.monotonic()
        self._grazinti_uzstrigusius()
        is_viso = 0
        try:
            while True:
                paimta, issiusta = self._siusti_partija(kiekis)
                is_viso += issiusta
                if paimta < kiekis or time.monotonic() - pradzia >= laiko_riba:
                    break
        finally:
            self._uzdaryti_kanalus()
        if is_viso:
            zurnalas.info("Išsiųsta pranešimų: %s", is_viso)
        return is_viso

    def siusti_partija(self, kiekis=PARTIJOS_DYDIS):
        """Išsiunčia vieną partiją ir grąžina sėkmingai išsiųstų pranešimų skaičių."""
        self._grazinti_uzstrigusius()
        try:
            return self._siusti_partija(kiekis)[1]
        finally:
            self._uzdaryti_kanalus()

    def _siusti_partija(self, kiekis):
        """Grąžina porą: kiek įrašų paimta iš eilės ir kiek iš jų išsiųsta."""
        irasai = self.eile.paimti_laukiancius(kiekis)
        issiusta = sum(1 for irasas in irasai if self._siusti_viena(irasas))
        return len(irasai), issiusta

    def _grazinti_uzstrigusius(self):
        grazinta = self.eile.grazinti_uzstrigusius()
        if grazinta:
            zurnalas.warning("Į eilę grąžinta užstrigusių įrašų: %s", grazinta)

    def _uzdaryti_kanalus(self):
        for kanalas in self.kanalai.values():
            try:
                kanalas.uzdaryti()
            except Exception:  # jungties uždarymo klaida neturi sustabdyti siuntėjo
                zurnalas.exception("Kanalo „%s“ uždaryti nepavyko", kanalas.kodas)

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
