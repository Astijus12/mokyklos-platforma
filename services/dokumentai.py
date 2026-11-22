"""Dokumentų generatoriai (aprašo 6 pav. klasė DokumentuGeneratorius ir jos paveldėtojos).

Visiems dokumentams bendri veiksmai aprašyti abstrakčioje klasėje:
1) numerio suteikimas (PZ-2026-0042) užrakinant skaitiklio eilutę (FR-D04);
2) PDF sudarymas su mokyklos rekvizitais ir poraštėje esančiu numeriu;
3) failo išsaugojimas ir SHA-256 kontrolinės sumos apskaičiavimas (FR-D05, NFR-11).
Paveldinčios klasės aprašo tik konkretaus dokumento turinį (metodas turinys()).

Failai saugomi kataloge DOKUMENTU_KATALOGAS (ne static/), todėl juos galima
atsisiųsti tik per maršrutą, kuris patikrina teises.
"""
import hashlib
import io
import os
from abc import ABC, abstractmethod
from datetime import date
from xml.sax.saxutils import escape

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.exc import IntegrityError

from models import Dokumentas, DokumentuSkaitiklis, db

# Šriftai su lietuviškomis raidėmis: Linux (Docker) – DejaVu, Windows – Arial
_SRIFTU_KANDIDATAI = (
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
)
SRIFTAS, SRIFTAS_PARYSKINTAS = "Tekstas", "Tekstas-Paryskintas"
_sriftai_uzregistruoti = False


def _uzregistruoti_sriftus():
    """Užregistruoja pirmą rastą šriftą. Jei nė vieno nėra – ReportLab „Vera“ (be ą, č, ę...)."""
    global _sriftai_uzregistruoti
    if _sriftai_uzregistruoti:
        return
    kandidatai = list(_SRIFTU_KANDIDATAI)
    if current_app.config.get("PDF_SRIFTAS"):
        kandidatai.insert(0, (current_app.config["PDF_SRIFTAS"], current_app.config.get("PDF_SRIFTAS_PARYSKINTAS")
                              or current_app.config["PDF_SRIFTAS"]))
    kandidatai.append((None, None))
    for paprastas, paryskintas in kandidatai:
        if paprastas is None:
            paprastas, paryskintas = "Vera.ttf", "VeraBd.ttf"
            current_app.logger.warning("Nerastas šriftas su lietuviškomis raidėmis, naudojamas Vera.")
        elif not (os.path.exists(paprastas) and os.path.exists(paryskintas)):
            continue
        pdfmetrics.registerFont(TTFont(SRIFTAS, paprastas))
        pdfmetrics.registerFont(TTFont(SRIFTAS_PARYSKINTAS, paryskintas))
        break
    _sriftai_uzregistruoti = True


def stiliai():
    """Pastraipų stiliai visiems dokumentams."""
    pagrindinis = ParagraphStyle("Pagrindinis", fontName=SRIFTAS, fontSize=11, leading=16)
    return {
        "pagrindinis": pagrindinis,
        "antraste": ParagraphStyle("Antraste", parent=pagrindinis, fontName=SRIFTAS_PARYSKINTAS,
                                   fontSize=14, leading=18, alignment=TA_CENTER, spaceAfter=2 * mm),
        "centras": ParagraphStyle("Centras", parent=pagrindinis, alignment=TA_CENTER),
        "skyrius": ParagraphStyle("Skyrius", parent=pagrindinis, fontName=SRIFTAS_PARYSKINTAS,
                                  spaceBefore=4 * mm, spaceAfter=1 * mm),
        "mazas": ParagraphStyle("Mazas", parent=pagrindinis, fontSize=9, leading=12, textColor=colors.grey),
    }


def tekstas(reiksme):
    """Naudotojo įvestas tekstas PDF pastraipai: ženklai < > & paverčiami saugiais."""
    return escape(str(reiksme or "")).replace("\n", "<br/>")


def lentele(eilutes, plociai, antraste=True):
    """Paprasta lentelė su rėmeliais (pirmoji eilutė – antraštė)."""
    st = stiliai()["pagrindinis"]
    duomenys = [[Paragraph(tekstas(langelis), st) for langelis in eilute] for eilute in eilutes]
    t = Table(duomenys, colWidths=[p * mm for p in plociai], repeatRows=1 if antraste else 0)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9") if antraste else colors.white),
    ]))
    return t


def kelias_diske(dokumentas):
    return os.path.join(current_app.config["DOKUMENTU_KATALOGAS"], dokumentas.failo_kelias)


def sha256(turinys):
    return hashlib.sha256(turinys).hexdigest()


def tikrinti_vientisuma(dokumentas):
    """FR-D05: ar failas diske nepakeistas (kontrolinė suma sutampa su įrašyta)."""
    try:
        with open(kelias_diske(dokumentas), "rb") as failas:
            return sha256(failas.read()) == dokumentas.sha256
    except OSError:
        return False


class DokumentuGeneratorius(ABC):
    """Abstrakti klasė: numeris, PDF, failas ir kontrolinė suma – visiems dokumentams vienodai."""

    tipo_kodas = None      # pvz., "PZ"
    pavadinimas = None     # pvz., "Pažyma" (PDF metaduomenims)

    def parengti(self, duomenys, mokinys=None, sukure=None):
        """Sukuria dokumentą ir grąžina Dokumentas įrašą. Commit atlieka kviečiantis kodas,
        kad numerio skaitiklio užraktas ir dokumento įrašas būtų vienoje transakcijoje."""
        _uzregistruoti_sriftus()
        numeris = self._suteikti_numeri()
        pdf = self._sudaryti_pdf(numeris, duomenys)
        dokumentas = Dokumentas(
            numeris=numeris,
            tipas=self.tipo_kodas,
            mokinio_id=mokinys.id if mokinys is not None else None,
            sukure_id=sukure.id if sukure is not None else None,
            failo_kelias=self._issaugoti(numeris, pdf),
            sha256=sha256(pdf),
        )
        db.session.add(dokumentas)
        return dokumentas

    @abstractmethod
    def turinys(self, duomenys):
        """Grąžina ReportLab elementų sąrašą (pastraipos, lentelės) – dokumento turinį."""

    # --- Bendri veiksmai -------------------------------------------------------------

    def _uzrakinti_skaitikli(self, metai):
        return db.session.execute(
            db.select(DokumentuSkaitiklis)
            .where(DokumentuSkaitiklis.tipas == self.tipo_kodas, DokumentuSkaitiklis.metai == metai)
            .with_for_update()
        ).scalar_one_or_none()

    def _suteikti_numeri(self):
        """Kitas numeris pagal tipą ir metus. Eilutė užrakinama (SELECT ... FOR UPDATE), todėl
        lygiagrečiai generuojami dokumentai gauna skirtingus numerius (FR-D04)."""
        metai = date.today().year
        skaitiklis = self._uzrakinti_skaitikli(metai)
        if skaitiklis is None:
            # Pirmas tų metų dokumentas: eilutė įterpiama (jei kitas procesas spėjo pirmas –
            # atšaukiamas tik šis įterpimas) ir užrakinama
            try:
                with db.session.begin_nested():
                    db.session.add(DokumentuSkaitiklis(tipas=self.tipo_kodas, metai=metai, paskutinis_nr=0))
            except IntegrityError:
                pass
            skaitiklis = self._uzrakinti_skaitikli(metai)
        skaitiklis.paskutinis_nr += 1
        return f"{self.tipo_kodas}-{metai}-{skaitiklis.paskutinis_nr:04d}"

    def _sudaryti_pdf(self, numeris, duomenys):
        konf = current_app.config
        buferis = io.BytesIO()
        dokumentas = SimpleDocTemplate(
            buferis, pagesize=A4,
            leftMargin=25 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
            title=f"{self.pavadinimas} {numeris}", author=konf.get("MOKYKLOS_PAVADINIMAS", ""),
        )
        st = stiliai()
        rekvizitai = [
            Paragraph(tekstas(konf.get("MOKYKLOS_PAVADINIMAS", "")), st["antraste"]),
            Paragraph(tekstas(konf.get("MOKYKLOS_REKVIZITAI", "")), st["centras"]),
            Spacer(1, 10 * mm),
        ]

        def poraste(drobe, _dokumentas):
            drobe.saveState()
            drobe.setFont(SRIFTAS, 8)
            drobe.setFillColor(colors.grey)
            drobe.drawString(25 * mm, 12 * mm, f"Dokumento nr. {numeris} · sugeneruota sistemoje "
                                                f"{date.today():%Y-%m-%d}")
            drobe.drawRightString(A4[0] - 20 * mm, 12 * mm, f"{drobe.getPageNumber()} psl.")
            drobe.restoreState()

        # Numeris perduodamas ir turiniui, nes jis rašomas dokumento antraštėje
        turinys = self.turinys({**duomenys, "numeris": numeris})
        dokumentas.build(rekvizitai + turinys, onFirstPage=poraste, onLaterPages=poraste)
        return buferis.getvalue()

    def _issaugoti(self, numeris, pdf):
        """Išsaugo PDF ir grąžina kelią, santykinį su DOKUMENTU_KATALOGAS."""
        santykinis = f"{date.today().year}/{numeris}.pdf"
        kelias = os.path.join(current_app.config["DOKUMENTU_KATALOGAS"], santykinis)
        os.makedirs(os.path.dirname(kelias), exist_ok=True)
        with open(kelias, "wb") as failas:
            failas.write(pdf)
        return santykinis


def _antraste(pavadinimas, numeris, vieta=""):
    st = stiliai()
    eilute = f"{date.today():%Y-%m-%d} Nr. {numeris}" + (f"<br/>{tekstas(vieta)}" if vieta else "")
    return [Paragraph(pavadinimas, st["antraste"]), Paragraph(eilute, st["centras"]), Spacer(1, 8 * mm)]


class PazymosGeneratorius(DokumentuGeneratorius):
    """Pažyma, kad mokinys mokosi mokykloje (FR-D03). duomenys: mokinys, paskirtis, numeris."""

    tipo_kodas = "PZ"
    pavadinimas = "Pažyma"

    def turinys(self, duomenys):
        st = stiliai()
        mokinys = duomenys["mokinys"]
        gimes = f" (gim. {mokinys.gimimo_data:%Y-%m-%d})" if mokinys.gimimo_data else ""
        mokykla = current_app.config.get("MOKYKLOS_PAVADINIMAS_KILMININKAS", "")
        klase = mokinys.klase
        elementai = _antraste("PAŽYMA", duomenys["numeris"], current_app.config.get("MOKYKLOS_VIETOVE", ""))
        elementai += [
            Paragraph(
                f"Pažymima, kad <b>{tekstas(mokinys.pilnas_vardas)}</b>{tekstas(gimes)} "
                f"{tekstas(klase.mokslo_metai)} mokslo metais mokosi {tekstas(mokykla)} "
                f"{tekstas(klase.pavadinimas)} klasėje.", st["pagrindinis"]),
            Spacer(1, 4 * mm),
            Paragraph(f"Pažymos paskirtis: {tekstas(duomenys['paskirtis'])}.", st["pagrindinis"]),
            Spacer(1, 25 * mm),
            Paragraph("Direktorius (-ė) arba įgaliotas asmuo&nbsp;&nbsp;&nbsp;______________________",
                      st["pagrindinis"]),
        ]
        return elementai



class ProtokoloGeneratorius(DokumentuGeneratorius):
    """VGK posėdžio protokolo projektas iš įrašytų duomenų (FR-V07). duomenys: posedis."""

    tipo_kodas = "PR"
    pavadinimas = "VGK posėdžio protokolas"

    def turinys(self, duomenys):
        st = stiliai()
        posedis = duomenys["posedis"]
        elementai = _antraste("VAIKO GEROVĖS KOMISIJOS POSĖDŽIO PROTOKOLAS (PROJEKTAS)",
                              duomenys["numeris"], current_app.config.get("MOKYKLOS_VIETOVE", ""))
        elementai.append(Paragraph(
            f"Posėdžio data ir laikas: {posedis.data:%Y-%m-%d} {posedis.laikas:%H:%M}. "
            f"Vieta: {tekstas(posedis.vieta)}.", st["pagrindinis"]))

        dalyvavo = [d for d in posedis.dalyviai if d.dalyvavo]
        elementai.append(Paragraph("Dalyvavo", st["skyrius"]))
        if dalyvavo:
            elementai.append(lentele(
                [["Vardas, pavardė", "Vaidmuo", "Pasižadėjimas"]] +
                [[d.vardas_pavarde, d.vaidmens_pavadinimas, "Pasirašytas" if d.pasizadejimas else "Nepasirašytas"]
                 for d in dalyvavo],
                [70, 55, 40]))
        else:
            elementai.append(Paragraph("Dalyvavimas nepažymėtas.", st["pagrindinis"]))

        elementai.append(Paragraph("Darbotvarkė ir nutarimai", st["skyrius"]))
        for svarstymas in posedis.svarstymai:
            atvejis = svarstymas.atvejis
            elementai.append(Paragraph(
                f"{svarstymas.eiles_nr}. {tekstas(atvejis.mokinys.pilnas_vardas)} "
                f"({tekstas(atvejis.mokinys.klase.pavadinimas)} kl.). Kreipimosi priežastis: "
                f"{tekstas(atvejis.priezastis)}", st["pagrindinis"]))
            elementai.append(Paragraph(f"<b>Nutarta:</b> {tekstas(svarstymas.nutarimas or 'nutarimas neįrašytas')}",
                                       st["pagrindinis"]))
            if svarstymas.priemones:
                elementai.append(Spacer(1, 2 * mm))
                elementai.append(lentele(
                    [["Priemonė", "Atsakingas", "Terminas"]] +
                    [[p.aprasymas, p.atsakingas.pilnas_vardas if p.atsakingas else "", f"{p.terminas:%Y-%m-%d}"]
                     for p in svarstymas.priemones],
                    [95, 45, 25]))
            elementai.append(Spacer(1, 3 * mm))

        elementai += [
            Spacer(1, 15 * mm),
            Paragraph("Posėdžio pirmininkas (-ė)&nbsp;&nbsp;______________________", st["pagrindinis"]),
            Spacer(1, 8 * mm),
            Paragraph("Posėdžio sekretorius (-ė)&nbsp;&nbsp;______________________", st["pagrindinis"]),
            Spacer(1, 6 * mm),
            Paragraph("Protokolas konfidencialus: jame yra Vaiko gerovės komisijos duomenų.", st["mazas"]),
        ]
        return elementai


class AtaskaitosGeneratorius(DokumentuGeneratorius):
    """Laikotarpio suvestinė administracijai (FR-D06, FR-D07). duomenys: nuo, iki, statistika."""

    tipo_kodas = "AT"
    pavadinimas = "Ataskaita"

    def turinys(self, duomenys):
        st = stiliai()
        s = duomenys["statistika"]
        elementai = _antraste("VEIKLOS SUVESTINĖ", duomenys["numeris"])
        elementai.append(Paragraph(f"Laikotarpis: {duomenys['nuo']:%Y-%m-%d} – {duomenys['iki']:%Y-%m-%d}",
                                   st["centras"]))

        elementai.append(Paragraph("Mokiniai pagal klases", st["skyrius"]))
        elementai.append(lentele([["Klasė", "Mokinių"]] + [[k, str(n)] for k, n in s["klases"]] +
                                 [["Iš viso", str(s["mokiniu_is_viso"])]], [80, 40]))

        elementai.append(Paragraph("Vaiko gerovės komisija", st["skyrius"]))
        elementai.append(lentele([
            ["Rodiklis", "Reikšmė"],
            ["Užregistruota naujų atvejų", str(s["vgk_nauji"])],
            ["Įvykusių posėdžių", str(s["vgk_posedziai"])],
            ["Aktyvių atvejų laikotarpio pabaigoje", str(s["vgk_aktyvus"])],
            ["Priemonių su terminu laikotarpyje", str(s["priemones_is_viso"])],
            ["iš jų įvykdyta", str(s["priemones_ivykdyta"])],
            ["iš jų vėluoja", str(s["priemones_veluoja"])],
        ], [100, 40]))

        elementai.append(Paragraph("Pranešimai ir dokumentai", st["skyrius"]))
        elementai.append(lentele([
            ["Rodiklis", "Reikšmė"],
            ["Išsiųsta el. laiškų", str(s["issiusta_el_pastu"])],
            ["Pranešimų sistemos pranešimų centre", str(s["issiusta_sistemoje"])],
            ["Nepavyko išsiųsti", str(s["nepavyko"])],
            ["Parengta pažymų", str(s["pazymu"])],
        ], [100, 40]))
        return elementai
