"""Priminimų kūrėjas (aprašo 6 pav. klasė PriminimuKurejas, FR-A06).

Planuoklė kasdien (ir paleidus fono procesą) kviečia sukurti_priminimus().
Kiekvienai aktyviai priminimo taisyklei randami objektai, iki kurių datos liko
ne daugiau kaip taisyklės poslinkis dienų, ir apie juos paskelbiamas įvykis
tuo pačiu įvykių skirstytuvu. Kadangi į unikalų raktą įeina objekto data, tas
pats priminimas nesukuriamas du kartus, net jei užduotis paleidžiama kelis kartus,
o pakeitus renginio datą priminimas bus išsiųstas naujai datai.
"""
from datetime import date, timedelta

from models import AutomatizavimoTaisykle, Renginys, VgkPosedis, VgkPriemone, db
from services.ivykiai import IVYKIU_TIPAI, PRIMINIMU_TIPAI, IvykiuSkirstytuvas
from services.kalendorius import darbo_dienos_iki

# Kiek dienų į priekį ieškoti objektų (didžiausias prasmingas poslinkis)
PAIESKOS_LAIKOTARPIS = timedelta(days=60)


class PriminimuKurejas:
    """Sukuria priminimus apie artėjančius renginius, posėdžius ir priemonių terminus."""

    def __init__(self, skirstytuvas=None):
        self.skirstytuvas = skirstytuvas or IvykiuSkirstytuvas()

    @staticmethod
    def darbo_dienos_iki(data, nuo=None):
        return darbo_dienos_iki(data, nuo)

    def liko_dienu(self, ivykis, data, siandien):
        """Kiek dienų liko iki datos: darbo dienomis arba kalendorinėmis."""
        if ivykis.darbo_dienomis:
            return self.darbo_dienos_iki(data, siandien)
        return (data - siandien).days

    def _artejantys(self, tipas, siandien):
        """Poros (objektas, objekto data) pagal įvykio tipą."""
        iki = siandien + PAIESKOS_LAIKOTARPIS
        if tipas == "renginys_artejantis":
            renginiai = Renginys.query.filter(Renginys.pradzios_data.between(siandien, iki))
            return [(r, r.pradzios_data) for r in renginiai]
        if tipas == "vgk_posedis_artejantis":
            posedziai = VgkPosedis.query.filter(
                VgkPosedis.busena == VgkPosedis.SUPLANUOTAS, VgkPosedis.data.between(siandien, iki))
            return [(p, p.data) for p in posedziai]
        if tipas == "priemones_terminas_artejantis":
            priemones = VgkPriemone.query.filter(
                VgkPriemone.busena == VgkPriemone.PASKIRTA, VgkPriemone.terminas.between(siandien, iki))
            return [(p, p.terminas) for p in priemones]
        return []

    def sukurti_priminimus(self, data=None):
        """Sukuria šiandienos priminimus ir grąžina naujų eilės įrašų skaičių."""
        siandien = data or date.today()
        taisykles = (
            AutomatizavimoTaisykle.query
            .filter(AutomatizavimoTaisykle.aktyvi.is_(True),
                    AutomatizavimoTaisykle.ivykio_tipas.in_(PRIMINIMU_TIPAI))
            .order_by(AutomatizavimoTaisykle.id)
            .all()
        )
        sukurta = 0
        for taisykle in taisykles:
            ivykis = IVYKIU_TIPAI[taisykle.ivykio_tipas]
            # Poslinkis 0 – priminimas objekto dieną; kitaip – nuo 1 iki poslinkio dienų iki datos
            # (jei fono procesas vakar neveikė, priminimas sukuriamas šiandien, o ne prarandamas)
            maziausiai = 0 if taisykle.poslinkis_d == 0 else 1
            for objektas, objekto_data in self._artejantys(taisykle.ivykio_tipas, siandien):
                liko = self.liko_dienu(ivykis, objekto_data, siandien)
                if maziausiai <= liko <= taisykle.poslinkis_d:
                    sukurta += self.skirstytuvas.skelbti(
                        taisykle.ivykio_tipas, objektas,
                        papildomas_raktas=objekto_data.isoformat(),
                        taisykles=[taisykle],
                    )
        db.session.commit()
        return sukurta
