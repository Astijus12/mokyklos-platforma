"""Pranešimų eilės testai su PostgreSQL: lygiagretus siuntimas ir lenktynės dėl rakto.

NFR-01: tas pats pranešimas tam pačiam gavėjui išsiunčiamas ne daugiau kaip
vieną kartą, net jei veikia du fono procesai. Čia du siuntėjai paleidžiami
atskirose gijose (kiekviena turi savo prisijungimą prie duomenų bazės).
"""
import threading
import time

from sqlalchemy import text

from models import EilesIrasas, db
from services.eile import PranesimuEile
from services.kanalai import Kanalas
from services.siuntejas import PranesimuSiuntejas


class _LetasKanalas(Kanalas):
    """Netikras el. pašto kanalas: įsimena išsiųstus įrašus ir dirba lėtai, kad gijos persidengtų."""
    kodas = "el_pastas"

    def __init__(self, issiusti, uzraktas):
        self.issiusti = issiusti
        self.uzraktas = uzraktas

    def siusti(self, irasas):
        time.sleep(0.02)
        with self.uzraktas:
            self.issiusti.append(irasas.id)
        return True


def test_du_lygiagretus_siuntejai_neissiuncia_to_paties_karto(app, tevas):
    for nr in range(40):
        db.session.add(EilesIrasas(gavejo_id=tevas.id, kanalas="el_pastas", tema="t", tekstas="t",
                                   unikalus_raktas=f"lygiagretus-{nr}"))
    db.session.commit()
    db.session.remove()

    issiusti, uzraktas = [], threading.Lock()
    startas = threading.Barrier(2)
    klaidos = []

    def siuntejo_gija():
        try:
            with app.app_context():
                startas.wait()
                siuntejas = PranesimuSiuntejas(kanalai=[_LetasKanalas(issiusti, uzraktas)])
                while siuntejas.siusti_partija(20):
                    pass
                db.session.remove()
        except Exception as klaida:  # gijos klaida perduodama testui
            klaidos.append(klaida)

    gijos = [threading.Thread(target=siuntejo_gija) for _ in range(2)]
    for gija in gijos:
        gija.start()
    for gija in gijos:
        gija.join(timeout=60)

    assert not klaidos
    assert len(issiusti) == 40
    assert len(set(issiusti)) == 40  # nė vienas įrašas neišsiųstas du kartus
    assert EilesIrasas.query.filter_by(busena=EilesIrasas.ISSIUSTAS).count() == 40


def test_lenktynes_del_to_paties_rakto(app, tevas):
    """Kitas procesas tą pačią akimirką įrašo tą patį raktą: įterpimas atšaukiamas tik
    išsaugojimo taške (SAVEPOINT), o likusi transakcija lieka tinkama."""
    kitas = db.engine.connect()
    kito_transakcija = kitas.begin()
    kitas.execute(text(
        "INSERT INTO pranesimu_eile (gavejo_id, kanalas, tema, tekstas, unikalus_raktas, busena, "
        "bandymai, siusti_po) VALUES (:g, 'el_pastas', 't', 't', 'lenktynes', 'laukia', 0, now())"
    ), {"g": tevas.id})

    def uzbaigti_kita():
        time.sleep(0.5)
        kito_transakcija.commit()
        kitas.close()

    gija = threading.Thread(target=uzbaigti_kita)
    gija.start()
    # Išankstinė patikra neįsipareigoto įrašo nemato, todėl INSERT laukia kito proceso
    # ir po jo įsipareigojimo gauna unikalumo klaidą
    rezultatas = PranesimuEile().prideti(tevas, "el_pastas", "lenktynes", "t", "t")
    gija.join()

    assert rezultatas is None
    db.session.commit()  # transakcija nesugadinta
    assert EilesIrasas.query.filter_by(unikalus_raktas="lenktynes").count() == 1
