"""Pranešimų eilė (aprašo 6 pav. klasė PranesimuEile ir 9 pav. būsenų diagrama).

Įrašo kelias: „Laukia“ -> „Siunčiamas“ -> „Išsiųstas“. Klaidos atveju įrašas
grįžta į „Laukia“ su vėlesniu siuntimo laiku (po 5 min., 30 min., 2 val.), o po
ketvirto nesėkmingo bandymo tampa „Nepavyko“. Nebeaktualus įrašas – „Atšauktas“.

Du apsaugos nuo dublikatų lygiai (NFR-01):
1. unikalus_raktas – to paties pranešimo antrą kartą įrašyti neleidžia duomenų bazė;
2. SELECT ... FOR UPDATE SKIP LOCKED – du fono procesai nepaima to paties įrašo.
"""
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models import EilesIrasas, db, utc_dabar

# Po kiek laiko kartoti po 1-ojo, 2-ojo ir 3-iojo nesėkmingo bandymo
PAKARTOJIMO_INTERVALAI = (timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=2))
MAKS_BANDYMU = len(PAKARTOJIMO_INTERVALAI) + 1  # iš viso 4 bandymai
# Jei fono procesas sustojo siųsdamas, įrašas po šio laiko grąžinamas į eilę
UZSTRIGIMO_LAIKAS = timedelta(minutes=15)


class PranesimuEile:
    """Eilės operacijos. Būsenas keičia tik ši klasė."""

    def prideti(self, gavejas, kanalas, raktas, tema, tekstas, taisykle=None, siusti_po=None):
        """Įrašo pranešimą į eilę. Jei toks raktas jau yra – grąžina None (dublikatas).

        Įrašas neišsaugomas (commit) – jį išsaugo kviečiantis kodas kartu su pačiu
        įvykiu, todėl, pvz., neišsaugojus skelbimo neatsiranda ir pranešimų.
        """
        jau_yra = db.session.query(EilesIrasas.id).filter_by(unikalus_raktas=raktas).first()
        if jau_yra:
            return None

        irasas = EilesIrasas(
            gavejo_id=gavejas.id,
            taisykles_id=taisykle.id if taisykle is not None else None,
            kanalas=kanalas,
            tema=tema[:200],
            tekstas=tekstas,
            unikalus_raktas=raktas,
            siusti_po=siusti_po or utc_dabar(),
        )
        # Įterpimas atskirame išsaugojimo taške (SAVEPOINT): jei kitas procesas tą pačią
        # akimirką įrašė tą patį raktą, atšaukiamas tik šis įterpimas, ne visa transakcija.
        try:
            with db.session.begin_nested():
                db.session.add(irasas)
        except IntegrityError:
            return None
        return irasas

    def paimti_laukiancius(self, kiekis=20):
        """Paima iki „kiekis“ laukiančių įrašų, kurių siuntimo laikas atėjo, ir pažymi „Siunčiamas“.

        PostgreSQL užrakina paimtas eilutes (FOR UPDATE), o SKIP LOCKED praleidžia
        kito proceso jau užrakintas – todėl du siuntėjai negauna tų pačių įrašų.
        SQLite šios sąlygos neturi, todėl ji ten tiesiog praleidžiama.
        """
        dabar = utc_dabar()
        uzklausa = (
            db.select(EilesIrasas)
            .where(EilesIrasas.busena == EilesIrasas.LAUKIA, EilesIrasas.siusti_po <= dabar)
            .order_by(EilesIrasas.siusti_po, EilesIrasas.id)
            .limit(kiekis)
            .with_for_update(skip_locked=True)
        )
        irasai = db.session.execute(uzklausa).scalars().all()
        for irasas in irasai:
            irasas.busena = EilesIrasas.SIUNCIAMAS
            irasas.siusti_po = dabar  # paėmimo laikas – užstrigusiems įrašams atpažinti
        db.session.commit()  # užraktai atlaisvinami, kiti procesai šių įrašų nebemato
        return irasai

    def pazymeti_issiusta(self, irasas):
        irasas.bandymai += 1
        irasas.busena = EilesIrasas.ISSIUSTAS
        irasas.issiusta = utc_dabar()
        irasas.klaida = None
        db.session.commit()

    def atideti(self, irasas, klaida):
        """Nepavykęs bandymas: kartoti vėliau arba (po 4 bandymų) pažymėti „Nepavyko“."""
        irasas.bandymai += 1
        irasas.klaida = (klaida or "Nežinoma klaida")[:1000]
        if irasas.bandymai >= MAKS_BANDYMU:
            irasas.busena = EilesIrasas.NEPAVYKO
        else:
            irasas.busena = EilesIrasas.LAUKIA
            irasas.siusti_po = utc_dabar() + PAKARTOJIMO_INTERVALAI[irasas.bandymai - 1]
        db.session.commit()
        return irasas

    def grazinti_uzstrigusius(self):
        """Įrašus, kurie per ilgai „Siunčiamas“ (procesas sustojo), grąžina į eilę."""
        riba = utc_dabar() - UZSTRIGIMO_LAIKAS
        kiekis = (
            EilesIrasas.query
            .filter(EilesIrasas.busena == EilesIrasas.SIUNCIAMAS, EilesIrasas.siusti_po < riba)
            .update({EilesIrasas.busena: EilesIrasas.LAUKIA}, synchronize_session=False)
        )
        db.session.commit()
        return kiekis

    def atsaukti_objekto(self, objekto_raktas):
        """FR-A08: atšaukia dar neišsiųstus pranešimus apie objektą (pvz., „renginys-15“).

        Įrašas neišsaugomas – tai daro kviečiantis kodas kartu su objekto pakeitimu.
        """
        return (
            EilesIrasas.query
            .filter(
                EilesIrasas.busena == EilesIrasas.LAUKIA,
                EilesIrasas.unikalus_raktas.startswith(f"{objekto_raktas}/", autoescape=True),
            )
            .update(
                {EilesIrasas.busena: EilesIrasas.ATSAUKTAS,
                 EilesIrasas.klaida: "Atšaukta: įvykis nebeaktualus."},
                synchronize_session=False,
            )
        )

    def pakartoti(self, irasas):
        """FR-A09: administratorius grąžina nepavykusį pranešimą į eilę."""
        if irasas.busena != EilesIrasas.NEPAVYKO:
            return False
        irasas.busena = EilesIrasas.LAUKIA
        irasas.bandymai = 0
        irasas.siusti_po = utc_dabar()
        irasas.klaida = None
        db.session.commit()
        return True

    def statistika(self, nuo):
        """Siuntimo suvestinė taisyklių puslapiui: kiek išsiųsta, laukia ir nepavyko."""
        def kiekis(*salygos):
            return db.session.query(func.count(EilesIrasas.id)).filter(*salygos).scalar()

        return {
            "issiusta": kiekis(EilesIrasas.busena == EilesIrasas.ISSIUSTAS, EilesIrasas.issiusta >= nuo),
            "laukia": kiekis(EilesIrasas.busena.in_([EilesIrasas.LAUKIA, EilesIrasas.SIUNCIAMAS]),
                             EilesIrasas.bandymai == 0),
            "kartojama": kiekis(EilesIrasas.busena == EilesIrasas.LAUKIA, EilesIrasas.bandymai > 0),
            "nepavyko": kiekis(EilesIrasas.busena == EilesIrasas.NEPAVYKO, EilesIrasas.siusti_po >= nuo),
        }
