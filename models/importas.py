"""Masinio importo modeliai – baigiamojo darbo dalis.

Lentelės: importo_sesijos, importo_eilutes (aprašo 11 pav.).
Kiekviena failo eilutė su tikrinimo rezultatu saugoma duomenų bazėje, todėl
peržiūra ir ataskaita parengiamos pakartotinai neskaitant failo.
"""
from models import db, utc_dabar, JSON_LAUKAS


class ImportoSesija(db.Model):
    """Įkelto failo suvestinė ir importo būsena."""
    __tablename__ = "importo_sesijos"

    PATIKRINTA = "patikrinta"
    IMPORTUOTA = "importuota"
    ATSAUKTA = "atsaukta"
    KLAIDA = "klaida"
    BUSENOS = {
        PATIKRINTA: "Patikrinta, laukia patvirtinimo",
        IMPORTUOTA: "Importuota",
        ATSAUKTA: "Atšaukta",
        KLAIDA: "Nepavyko",
    }

    id = db.Column(db.Integer, primary_key=True)
    vartotojo_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    failo_vardas = db.Column(db.String(255), nullable=False)
    busena = db.Column(db.String(20), nullable=False, default=PATIKRINTA)
    eiluciu_sk = db.Column(db.Integer, nullable=False, default=0)
    tinkamu_sk = db.Column(db.Integer, nullable=False, default=0)
    klaidu_sk = db.Column(db.Integer, nullable=False, default=0)
    sukurta = db.Column(db.DateTime, nullable=False, default=utc_dabar)

    vartotojas = db.relationship("User", foreign_keys=[vartotojo_id])
    eilutes = db.relationship(
        "ImportoEilute",
        back_populates="sesija",
        cascade="all, delete-orphan",
        order_by="ImportoEilute.eilutes_nr",
    )

    @property
    def busenos_pavadinimas(self):
        return self.BUSENOS.get(self.busena, self.busena)


class ImportoEilute(db.Model):
    """Viena failo eilutė, jos duomenys (JSON) ir tikrinimo rezultatas."""
    __tablename__ = "importo_eilutes"

    TINKAMA = "tinkama"
    KLAIDA = "klaida"
    DUBLIKATAS = "dublikatas"
    IRASYTA = "irasyta"
    BUSENOS = {
        TINKAMA: "Tinkama",
        KLAIDA: "Klaida",
        DUBLIKATAS: "Pasikartojanti",
        IRASYTA: "Įrašyta",
    }

    id = db.Column(db.Integer, primary_key=True)
    sesijos_id = db.Column(
        db.Integer, db.ForeignKey("importo_sesijos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    eilutes_nr = db.Column(db.Integer, nullable=False)
    duomenys = db.Column(JSON_LAUKAS, nullable=False)
    busena = db.Column(db.String(20), nullable=False)
    # Klaidų aprašymai, kiekvienas naujoje eilutėje
    klaidos = db.Column(db.Text, nullable=True)
    # Užpildomas įrašius eilutę – nuoroda į sukurtą mokinį
    mokinio_id = db.Column(
        db.Integer, db.ForeignKey("mokiniai.id", ondelete="SET NULL"), nullable=True
    )

    sesija = db.relationship("ImportoSesija", back_populates="eilutes")
    mokinys = db.relationship("Mokinys", foreign_keys=[mokinio_id])

    @property
    def busenos_pavadinimas(self):
        return self.BUSENOS.get(self.busena, self.busena)
