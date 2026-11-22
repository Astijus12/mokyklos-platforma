"""Vaiko gerovės komisijos (VGK) modeliai – baigiamojo darbo dalis.

Lentelės: vgk_atvejai, vgk_posedziai, vgk_svarstymai, vgk_dalyviai, vgk_priemones
(aprašo 10 pav. „VGK ir dokumentų dalies esybių ir ryšių diagrama“).

Būsenos saugomos trumpais kodais (pvz., "uzregistruotas"), o sąsajoje rodomi
pilni pavadinimai iš BUSENOS žodynų. Leistinus būsenų perėjimus tikrina
paslaugų sluoksnis (services/), ne maršrutai.
"""
from models import db, utc_dabar


class VgkAtvejis(db.Model):
    """Kreipimasis dėl mokinio ir jo nagrinėjimo būsena (aprašo 1.6 poskyris)."""
    __tablename__ = "vgk_atvejai"

    UZREGISTRUOTAS = "uzregistruotas"
    SVARSTOMAS = "svarstomas"
    TAIKOMOS_PRIEMONES = "taikomos_priemones"
    UZBAIGTAS = "uzbaigtas"
    BUSENOS = {
        UZREGISTRUOTAS: "Užregistruotas",
        SVARSTOMAS: "Svarstomas",
        TAIKOMOS_PRIEMONES: "Taikomos priemonės",
        UZBAIGTAS: "Užbaigtas",
    }

    id = db.Column(db.Integer, primary_key=True)
    mokinio_id = db.Column(
        db.Integer, db.ForeignKey("mokiniai.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Kas pateikė kreipimąsi; perkeltiems iš senos sistemos atvejams – nežinoma (NULL)
    pateike_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    priezastis = db.Column(db.Text, nullable=False)
    busena = db.Column(db.String(30), nullable=False, default=UZREGISTRUOTAS, index=True)
    sukurta = db.Column(db.DateTime, nullable=False, default=utc_dabar)
    uzbaigta = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        # Duomenų bazė pati neleidžia įrašyti neleistinos būsenos
        db.CheckConstraint(
            "busena IN ('uzregistruotas', 'svarstomas', 'taikomos_priemones', 'uzbaigtas')",
            name="ck_vgk_atvejai_busena",
        ),
    )

    mokinys = db.relationship("Mokinys", back_populates="vgk_atvejai")
    pateike = db.relationship("User", foreign_keys=[pateike_id])
    svarstymai = db.relationship(
        "VgkSvarstymas",
        back_populates="atvejis",
        cascade="all, delete-orphan",
        order_by="VgkSvarstymas.id",
    )

    @property
    def busenos_pavadinimas(self):
        return self.BUSENOS.get(self.busena, self.busena)

    @property
    def numeris(self):
        """Atvejo numeris sąsajoje, pvz., „2026-07“ (metai ir eilės numeris)."""
        return f"{self.sukurta.year}-{self.id:02d}"

    @property
    def yra_aktyvus(self):
        """Atvejis aktyvus, kol jis neužbaigtas."""
        return self.busena != self.UZBAIGTAS


class VgkPosedis(db.Model):
    """Komisijos posėdis: data, laikas, vieta, būsena ir protokolas."""
    __tablename__ = "vgk_posedziai"

    JUODRASTIS = "juodrastis"
    SUPLANUOTAS = "suplanuotas"
    IVYKES = "ivykes"
    ATSAUKTAS = "atsauktas"
    BUSENOS = {
        JUODRASTIS: "Juodraštis",
        SUPLANUOTAS: "Suplanuotas",
        IVYKES: "Įvykęs",
        ATSAUKTAS: "Atšauktas",
    }

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, index=True)
    laikas = db.Column(db.Time, nullable=False)
    vieta = db.Column(db.String(200), nullable=False)
    busena = db.Column(db.String(30), nullable=False, default=JUODRASTIS, index=True)
    # FR-V04: jei iki posėdžio liko mažiau nei 5 darbo dienos, būtina nurodyti priežastį
    skubos_priezastis = db.Column(db.Text, nullable=True)
    protokolo_id = db.Column(
        db.Integer, db.ForeignKey("dokumentai.id", ondelete="SET NULL"), nullable=True
    )

    svarstymai = db.relationship(
        "VgkSvarstymas",
        back_populates="posedis",
        cascade="all, delete-orphan",
        order_by="VgkSvarstymas.eiles_nr",
    )
    dalyviai = db.relationship(
        "VgkDalyvis",
        back_populates="posedis",
        cascade="all, delete-orphan",
        order_by="VgkDalyvis.id",
    )
    protokolas = db.relationship("Dokumentas", foreign_keys=[protokolo_id])

    @property
    def busenos_pavadinimas(self):
        return self.BUSENOS.get(self.busena, self.busena)


class VgkSvarstymas(db.Model):
    """Atvejo svarstymas konkrečiame posėdyje ir priimtas nutarimas.

    Ši lentelė susieja atvejus ir posėdžius ryšiu „daug su daug“: tas pats
    atvejis gali būti svarstomas keliuose posėdžiuose, o posėdyje – keli atvejai.
    """
    __tablename__ = "vgk_svarstymai"

    id = db.Column(db.Integer, primary_key=True)
    posedzio_id = db.Column(
        db.Integer, db.ForeignKey("vgk_posedziai.id", ondelete="CASCADE"), nullable=False, index=True
    )
    atvejo_id = db.Column(
        db.Integer, db.ForeignKey("vgk_atvejai.id", ondelete="CASCADE"), nullable=False, index=True
    )
    eiles_nr = db.Column(db.Integer, nullable=False, default=1)
    nutarimas = db.Column(db.Text, nullable=True)

    __table_args__ = (
        # Tas pats atvejis į to paties posėdžio darbotvarkę įtraukiamas tik kartą
        db.UniqueConstraint("posedzio_id", "atvejo_id", name="uq_vgk_svarstymai_posedis_atvejis"),
    )

    posedis = db.relationship("VgkPosedis", back_populates="svarstymai")
    atvejis = db.relationship("VgkAtvejis", back_populates="svarstymai")
    priemones = db.relationship(
        "VgkPriemone",
        back_populates="svarstymas",
        cascade="all, delete-orphan",
        order_by="VgkPriemone.terminas",
    )


class VgkDalyvis(db.Model):
    """Posėdžio dalyvis: sistemos naudotojas arba kviestinis asmuo be paskyros."""
    __tablename__ = "vgk_dalyviai"

    VAIDMENYS = {
        "pirmininkas": "Komisijos pirmininkas",
        "sekretorius": "Komisijos sekretorius",
        "narys": "Komisijos narys",
        "tevas": "Tėvas (globėjas)",
        "klases_vadovas": "Klasės vadovas",
        "kviestinis": "Kviestinis asmuo",
    }

    id = db.Column(db.Integer, primary_key=True)
    posedzio_id = db.Column(
        db.Integer, db.ForeignKey("vgk_posedziai.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vartotojo_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Vardas saugomas ir sistemos naudotojams, kad protokolas nepasikeistų pašalinus paskyrą
    vardas_pavarde = db.Column(db.String(160), nullable=False)
    vaidmuo = db.Column(db.String(30), nullable=False)
    dalyvavo = db.Column(db.Boolean, nullable=False, default=False)
    # Pasirašytas konfidencialumo pasižadėjimas
    pasizadejimas = db.Column(db.Boolean, nullable=False, default=False)

    posedis = db.relationship("VgkPosedis", back_populates="dalyviai")
    vartotojas = db.relationship("User", foreign_keys=[vartotojo_id])

    @property
    def vaidmens_pavadinimas(self):
        return self.VAIDMENYS.get(self.vaidmuo, self.vaidmuo)


class VgkPriemone(db.Model):
    """Posėdyje paskirta pagalbos priemonė su atsakingu asmeniu ir terminu."""
    __tablename__ = "vgk_priemones"

    PASKIRTA = "paskirta"
    IVYKDYTA = "ivykdyta"
    VELUOJA = "veluoja"
    BUSENOS = {
        PASKIRTA: "Vykdoma",
        IVYKDYTA: "Įvykdyta",
        VELUOJA: "Vėluoja",
    }

    id = db.Column(db.Integer, primary_key=True)
    svarstymo_id = db.Column(
        db.Integer, db.ForeignKey("vgk_svarstymai.id", ondelete="CASCADE"), nullable=False, index=True
    )
    atsakingo_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    aprasymas = db.Column(db.Text, nullable=False)
    terminas = db.Column(db.Date, nullable=False, index=True)
    busena = db.Column(db.String(20), nullable=False, default=PASKIRTA, index=True)
    rezultatas = db.Column(db.Text, nullable=True)

    svarstymas = db.relationship("VgkSvarstymas", back_populates="priemones")
    atsakingas = db.relationship("User", foreign_keys=[atsakingo_id])

    @property
    def busenos_pavadinimas(self):
        return self.BUSENOS.get(self.busena, self.busena)
