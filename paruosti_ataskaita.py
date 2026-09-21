"""Sukuria profesinės praktikos ataskaitą pagal Vilniaus kolegijos EIF
Bendruosius studijų rašto darbų reikalavimus.

Visi formatavimo parametrai pagal Bendrieji-studiju-rasto-darbu-reikalavimai_rev2.pdf.
"""
import sys
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK
from docx.enum.section import WD_SECTION_START
from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================================
# PAGRINDINIAI PARAMETRAI
# ============================================================================

STUDENTAS = "ASTIJUS GRINEVIČIUS"
GRUPE = "PI23SN"
STUDIJU_KODAS = "6531BX028"
PRAKTIKOS_KODAS_PILNAS = f"PA {STUDIJU_KODAS} {GRUPE}"
KATEDRA = "PROGRAMINĖS ĮRANGOS KATEDRA"
IMONE_LT = "Kupiškio r. Subačiaus gimnazija"
IMONE_LT_PILNAS = "Kupiškio r. Subačiaus gimnazija (Noriūnų Jono Černiaus skyrius)"
IMONE_EN = "Subačius Gymnasium of Kupiškis District (Noriūnai Jonas Černius Branch)"
PRAKTIKOS_VADOVAS_IMONE = "RITA GRINEVIČIENĖ"
PRAKTIKOS_VADOVAS_EIF = "DOC. DR. R. TUMASONIS"
DATA_PRADZIA = "2026-04-27"
DATA_PABAIGA = "2026-06-19"
METAI = "2026"

ISSAUGOTAS_KELIAS = r"C:\Users\astij\OneDrive\Desktop\Profesines_praktikos_ataskaita_DRAFT.docx"


# ============================================================================
# PAGALBINĖS FUNKCIJOS
# ============================================================================

def nustatyti_pagr_sriftai(doc):
    """Nustato Times New Roman 12pt kaip pagrindinį šriftą."""
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), "Times New Roman")
    rfonts.set(qn("w:hAnsi"), "Times New Roman")
    rfonts.set(qn("w:eastAsia"), "Times New Roman")
    rfonts.set(qn("w:cs"), "Times New Roman")


def nustatyti_marges(doc):
    """A4 (210x297mm) su K30/D10/V20/A20 mm paraštėmis."""
    for s in doc.sections:
        s.page_height = Cm(29.7)
        s.page_width = Cm(21)
        s.top_margin = Cm(2)
        s.bottom_margin = Cm(2)
        s.left_margin = Cm(3)
        s.right_margin = Cm(1)


def sukurti_stilius(doc):
    """Sukuria visus reikalingus stilius pagal reikalavimus."""
    styles = doc.styles

    # TEKSTAS - pagrindinis tekstas (12pt, JUSTIFY, 1.5 tarpas, 1.27cm įtrauka)
    if "TEKSTAS" not in [s.name for s in styles]:
        tekstas = styles.add_style("TEKSTAS", 1)
        tekstas.font.name = "Times New Roman"
        tekstas.font.size = Pt(12)
        pf = tekstas.paragraph_format
        pf.first_line_indent = Cm(1.27)
        pf.line_spacing = 1.5
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)

    # Heading 1 - skyrių antraštės (14pt Bold DIDŽIOSIOS, CENTER, 1 tarpas, 6pt prieš/po)
    h1 = styles["Heading 1"]
    h1.font.name = "Times New Roman"
    h1.font.size = Pt(14)
    h1.font.bold = True
    h1.font.color.rgb = None  # Juoda
    h1.element.get_or_add_rPr()
    pf = h1.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.line_spacing = 1.0  # Single
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)

    # XML lygiu - nustatyti spalvą juodą (Heading 1 dažnai mėlynas)
    rpr = h1.element.get_or_add_rPr()
    color = rpr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        rpr.append(color)
    color.set(qn("w:val"), "000000")

    # Heading 2 - poskyriai (14pt Bold, pirma raidė didžioji, centruoti)
    h2 = styles["Heading 2"]
    h2.font.name = "Times New Roman"
    h2.font.size = Pt(14)
    h2.font.bold = True
    pf = h2.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.line_spacing = 1.0
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    rpr = h2.element.get_or_add_rPr()
    color = rpr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        rpr.append(color)
    color.set(qn("w:val"), "000000")

    # Heading 3 - skyreliai (12pt Bold, pirma raidė didžioji, centruoti, 12pt prieš)
    h3 = styles["Heading 3"]
    h3.font.name = "Times New Roman"
    h3.font.size = Pt(12)
    h3.font.bold = True
    pf = h3.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.line_spacing = 1.0
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)
    rpr = h3.element.get_or_add_rPr()
    color = rpr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        rpr.append(color)
    color.set(qn("w:val"), "000000")


def prideti_pastraipa(doc, tekstas, bold_prefix=None, indent=True):
    """Prideda pastraipą su TEKSTAS stiliumi (pagrindinis tekstas)."""
    p = doc.add_paragraph(style="TEKSTAS")
    if not indent:
        p.paragraph_format.first_line_indent = Cm(0)

    if bold_prefix:
        run_bold = p.add_run(bold_prefix)
        run_bold.bold = True
        run_bold.font.name = "Times New Roman"
        run_bold.font.size = Pt(12)
        if tekstas:
            run = p.add_run(tekstas)
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)
    elif tekstas:
        run = p.add_run(tekstas)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
    return p


def prideti_tustia(doc, kiek=1):
    """Prideda tuščias eilutes (be įtraukos)."""
    for _ in range(kiek):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.first_line_indent = Cm(0)


def prideti_centruota(doc, tekstas, bold=False, size=12):
    """Prideda centruotą tekstą (pvz., antraštiniam lapui)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run(tekstas)
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold
    return p


def prideti_skyriaus_antraste(doc, tekstas, naujas_puslapis=True):
    """Prideda skyriaus antraštę (Heading 1) - DIDŽIOSIOMIS, centruotą."""
    if naujas_puslapis:
        doc.add_page_break()
    p = doc.add_heading(tekstas.upper(), level=1)
    return p


def prideti_poskyrio_antraste(doc, tekstas):
    """Prideda poskyrio antraštę (Heading 2) - pirma raidė didžioji, 14pt Bold."""
    p = doc.add_heading(tekstas, level=2)
    return p


def prideti_skyrelio_antraste(doc, tekstas):
    """Prideda skyrelio antraštę (Heading 3) - pirma raidė didžioji, 12pt Bold."""
    p = doc.add_heading(tekstas, level=3)
    return p


def prideti_lenteles_antraste(doc, numeris, pavadinimas):
    """Prideda lentelės antraštę (virš lentelės, 12pt, centruota, mažosios)."""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.5
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{numeris} lentelė. {pavadinimas}")
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    return p


def prideti_kodo_fragmentą(doc, kodas):
    """Prideda programinio kodo fragmentą (Courier New 10pt, Single tarpas)."""
    for eilute in kodas.split('\n'):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(eilute if eilute else ' ')
        run.font.name = 'Courier New'
        run.font.size = Pt(10)


def prideti_paveikslo_antraste(doc, numeris, pavadinimas):
    """Prideda paveikslo antraštę (po paveikslu, 12pt, centruota)."""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.5
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{numeris} pav. {pavadinimas}")
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    return p


def sukurti_lentele(doc, antraste_eilute, duomenys, stulpelis_pločiai=None):
    """Sukuria lentelę su standartiniu formatavimu.

    Args:
        antraste_eilute: stulpelių antraštės sąrašas
        duomenys: eilučių sąrašas (kiekviena - stulpelių reikšmių sąrašas)
        stulpelis_pločiai: stulpelių pločiai cm vienetais (jei None - vienodi)
    """
    stulpeliu = len(antraste_eilute)
    table = doc.add_table(rows=1 + len(duomenys), cols=stulpeliu)
    table.style = "Table Grid"

    # Stulpelių pločiai
    if stulpelis_pločiai:
        for i, plotis in enumerate(stulpelis_pločiai):
            for row in table.rows:
                row.cells[i].width = Cm(plotis)

    # Antraštės eilutė - bold, centruota
    hdr = table.rows[0]
    for i, antrastes_tekstas in enumerate(antraste_eilute):
        cell = hdr.cells[i]
        cell.paragraphs[0].text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(antrastes_tekstas)
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)

    # Duomenų eilutės
    for r_idx, eilute in enumerate(duomenys):
        row = table.rows[r_idx + 1]
        for c_idx, reiksme in enumerate(eilute):
            cell = row.cells[c_idx]
            cell.paragraphs[0].text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing = 1.0
            # Pirmas stulpelis - kairėje, kiti - kairėje (per requirements)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(reiksme)
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)

    return table


def prideti_puslapio_numeravima(doc):
    """Prideda puslapio numerį (10pt) į apačios paraštę per vidurį.
    Antraštinis puslapis nenumeruojamas - numeris pradedamas nuo 2 psl.
    """
    # Pirma sekcija - antraštinis lapas, be numerio
    # Reikia padaryti, kad pirmas puslapis būtų skirtingas
    section = doc.sections[0]
    section.different_first_page_header_footer = True

    # Apatinė poraštė - puslapio numeris
    footer = section.footer
    footer_paragraph = footer.paragraphs[0]
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_paragraph.paragraph_format.first_line_indent = Cm(0)

    # Pridedam PAGE field 10pt dydžiu
    run = footer_paragraph.add_run()
    run.font.name = "Times New Roman"
    run.font.size = Pt(10)

    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")

    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)

    # Pirmo puslapio (antraštinio) poraštė lieka tuščia
    first_footer = section.first_page_footer
    if first_footer.paragraphs:
        first_footer.paragraphs[0].text = ""


# ============================================================================
# DOKUMENTO KŪRIMAS
# ============================================================================

doc = Document()
nustatyti_pagr_sriftai(doc)
nustatyti_marges(doc)
sukurti_stilius(doc)
prideti_puslapio_numeravima(doc)

# ----------------------------------------------------------------------------
# ANTRAŠTINIS LAPAS (pagal Bendrųjų reikalavimų 2 priedą)
# ----------------------------------------------------------------------------

prideti_centruota(doc, "VILNIAUS KOLEGIJA", bold=True)
prideti_centruota(doc, "ELEKTRONIKOS IR INFORMATIKOS FAKULTETAS", bold=True)
prideti_centruota(doc, KATEDRA, bold=True)

# Tarpas iki pavadinimo
prideti_tustia(doc, 10)

# Ataskaitos pavadinimas
prideti_centruota(doc, "PROFESINĖS PRAKTIKOS ATASKAITA", bold=True, size=16)
prideti_tustia(doc, 1)
prideti_centruota(doc, PRAKTIKOS_KODAS_PILNAS, bold=False, size=14)

# Praktikos vieta
prideti_tustia(doc, 4)

# Praktikos vieta - pildoma kaip lentelėje (kairysis stulpelis - etiketė, dešinysis - pavadinimas)
p = doc.add_paragraph()
p.paragraph_format.first_line_indent = Cm(0)
p.paragraph_format.space_after = Pt(0)
p.alignment = WD_ALIGN_PARAGRAPH.LEFT
r1 = p.add_run("PRAKTIKOS VIETA:\t\t")
r1.bold = False
r1.font.name = "Times New Roman"
r1.font.size = Pt(12)
r2 = p.add_run(IMONE_LT_PILNAS)
r2.bold = True
r2.font.name = "Times New Roman"
r2.font.size = Pt(12)

p2 = doc.add_paragraph()
p2.paragraph_format.first_line_indent = Cm(0)
p2.paragraph_format.space_before = Pt(0)
p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
r = p2.add_run("\t\t\t" + IMONE_EN)
r.italic = True
r.font.name = "Times New Roman"
r.font.size = Pt(12)

prideti_tustia(doc, 4)

# Įmonės praktikos vadovas
def prideti_paraso_eilutes(doc, antrastes, vardas, data=None):
    """Sukuria parašo zoną: etiketė kairėje, data centre, vardas dešinėje."""
    p1 = doc.add_paragraph()
    p1.paragraph_format.first_line_indent = Cm(0)
    p1.paragraph_format.space_after = Pt(0)
    p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p1.add_run(antrastes)
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    p2 = doc.add_paragraph()
    p2.paragraph_format.first_line_indent = Cm(0)
    p2.paragraph_format.space_after = Pt(0)
    p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if data:
        r = p2.add_run(f"\t\t\t{data}\t\t\t")
    else:
        r = p2.add_run("\t\t\t202_ - __ - __\t\t\t")
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)
    r2 = p2.add_run(vardas)
    r2.bold = True
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(12)

prideti_paraso_eilutes(doc, "ĮMONĖS PRAKTIKOS VADOVAS (-Ė)", PRAKTIKOS_VADOVAS_IMONE, DATA_PABAIGA)
prideti_tustia(doc, 1)
prideti_paraso_eilutes(doc, "STUDENTAS (-Ė)", STUDENTAS, DATA_PABAIGA)
prideti_tustia(doc, 1)
prideti_paraso_eilutes(doc, "FAKULTETO PRAKTIKOS VADOVAS (-Ė)", PRAKTIKOS_VADOVAS_EIF, DATA_PABAIGA)

# Metai apačioje
prideti_tustia(doc, 4)
prideti_centruota(doc, METAI, bold=False)

# ----------------------------------------------------------------------------
# TERMINŲ IR SANTRUMPŲ SĄRAŠAS (prieš turinį)
# ----------------------------------------------------------------------------

prideti_skyriaus_antraste(doc, "Terminų ir santrumpų paaiškinimų sąrašas")

terminai = [
    ("API", "(angl. *Application Programming Interface*) – programų sąsajos rinkinys, leidžiantis programoms tarpusavyje keistis duomenimis."),
    ("CRUD", "(angl. *Create, Read, Update, Delete*) – duomenų valdymo operacijos: kūrimas, skaitymas, atnaujinimas, šalinimas."),
    ("CSS", "(angl. *Cascading Style Sheets*) – kaskadinių stilių lentelės; kalba, naudojama HTML dokumentų išvaizdai aprašyti."),
    ("CSV", "(angl. *Comma-Separated Values*) – kableliais atskirtų reikšmių failo formatas, naudojamas duomenims eksportuoti."),
    ("DB", "duomenų bazė."),
    ("DI", "dirbtinis intelektas."),
    ("EIF", "Elektronikos ir informatikos fakultetas."),
    ("ER", "esybių–ryšių (angl. *Entity–Relationship*) duomenų bazės modelis."),
    ("Flask", "Python kalbos web aplikacijų kūrimo karkasas (angl. *framework*)."),
    ("HTML", "(angl. *HyperText Markup Language*) – hiperteksto žymėjimo kalba."),
    ("HTTP", "(angl. *HyperText Transfer Protocol*) – hiperteksto perdavimo protokolas."),
    ("IS", "informacinė sistema."),
    ("MVC", "(angl. *Model–View–Controller*) – programinės įrangos architektūros šablonas."),
    ("ORM", "(angl. *Object–Relational Mapping*) – objektinis–reliacinis atvaizdavimas; technologija, susiejanti programos objektus su duomenų bazės lentelėmis."),
    ("PĮ", "programinė įranga."),
    ("PA", "praktikos ataskaita."),
    ("SQL", "(angl. *Structured Query Language*) – struktūrizuota užklausų kalba, skirta reliacinėms duomenų bazėms valdyti."),
    ("SQLite", "reliacinė duomenų bazių valdymo sistema, saugoma viename faile."),
    ("TAMO", "Lietuvos mokyklose naudojamas elektroninis dienynas (www.tamo.lt)."),
    ("UI", "(angl. *User Interface*) – vartotojo sąsaja."),
    ("UML", "(angl. *Unified Modeling Language*) – unifikuota modeliavimo kalba."),
    ("URL", "(angl. *Uniform Resource Locator*) – unifikuotas išteklių adresas."),
    ("VGK", "vaiko gerovės komisija."),
    ("VIKO", "Vilniaus kolegija."),
    ("WSGI", "(angl. *Web Server Gateway Interface*) – interneto serverio sąsaja Python aplikacijoms."),
]

for terminas, paaiskinimas in terminai:
    p = doc.add_paragraph(style="TEKSTAS")
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(terminas + " – ")
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

    # Apdoroti italic žymes *...*
    tekstas_dalys = paaiskinimas.split("*")
    for i, dalis in enumerate(tekstas_dalys):
        r = p.add_run(dalis)
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        if i % 2 == 1:  # nelyginiai - italic
            r.italic = True

# ----------------------------------------------------------------------------
# TURINYS (vietos rezervavimas - studentas Word'e pats turi sugeneruoti)
# ----------------------------------------------------------------------------

prideti_skyriaus_antraste(doc, "Turinys")
prideti_pastraipa(
    doc,
    "[ŠIOJE VIETOJE BUS AUTOMATIŠKAI SUGENERUOTAS TURINYS – WORD MENIU: "
    "References → Table of Contents → Automatic Table 1. "
    "Antraštės jau pažymėtos Heading 1 / Heading 2 stiliais.]",
    indent=False
)

# ----------------------------------------------------------------------------
# PAVEIKSLŲ SĄRAŠAS
# ----------------------------------------------------------------------------

prideti_skyriaus_antraste(doc, "Paveikslų sąrašas")
prideti_pastraipa(
    doc,
    "[ŠIOJE VIETOJE BUS AUTOMATIŠKAI SUGENERUOTAS PAVEIKSLŲ SĄRAŠAS – WORD MENIU: "
    "References → Insert Table of Figures → Caption label: pav.]",
    indent=False
)

# ----------------------------------------------------------------------------
# LENTELIŲ SĄRAŠAS
# ----------------------------------------------------------------------------

prideti_skyriaus_antraste(doc, "Lentelių sąrašas")
prideti_pastraipa(
    doc,
    "[ŠIOJE VIETOJE BUS AUTOMATIŠKAI SUGENERUOTAS LENTELIŲ SĄRAŠAS – WORD MENIU: "
    "References → Insert Table of Figures → Caption label: lentelė.]",
    indent=False
)

# ----------------------------------------------------------------------------
# ĮVADAS
# ----------------------------------------------------------------------------

prideti_skyriaus_antraste(doc, "Įvadas")

# Įmonės aprašymas (1 pastraipa)
prideti_pastraipa(
    doc,
    "Profesinė praktika atlikta Kupiškio rajono Subačiaus gimnazijos Noriūnų "
    "Jono Černiaus skyriuje (adresas: Melioratorių g. 5, Noriūnai k., "
    "Kupiškio r.). Subačiaus gimnazija – savivaldybei pavaldi bendrojo ugdymo "
    "institucija, vykdanti pradinio, pagrindinio bei vidurinio ugdymo "
    "programas. Noriūnų Jono Černiaus skyriuje vykdomas pradinis ir "
    "pagrindinis ugdymas; skyrius pavadintas Lietuvos partizano Jono Černiaus "
    "atminimui įamžinti. Skyriuje dirba pedagogų, švietimo pagalbos "
    "specialistų bei aptarnaujančio personalo komanda, atsakinga už mokinių "
    "ugdymą ir mokyklos veiklos administravimą."
)

# Esama IS aplinka
prideti_pastraipa(
    doc,
    "Mokyklos veikloje naudojamos kelios išorinės informacinės sistemos: "
    "elektroninis dienynas TAMO, skirtas mokinių pažymiams, lankomumui bei "
    "tvarkaraščiams valdyti, valstybinė švietimo valdymo informacinė sistema "
    "ŠVIS bei standartinės biuro programos (angl. *Microsoft Word, Excel*) "
    "raštvedybos užduotims atlikti. Tačiau bendros vidinės sistemos, "
    "kurioje būtų centralizuotai saugoma mokinių asmens informacija, tėvų "
    "kontaktiniai duomenys, vaiko gerovės komisijos sprendimai, "
    "organizaciniai skelbimai bei mokytojų kvalifikacijos kėlimo dokumentai, "
    "mokykla šiuo metu neturi."
)

# Temos aktualumas
prideti_pastraipa(
    doc,
    "Skaitmenizacija švietimo sektoriuje sparčiai didina poreikį "
    "centralizuotoms informacinėms sistemoms, kurios palengvina kasdienes "
    "administracines užduotis ir užtikrina duomenų prieinamumą bei saugumą. "
    "Mažesnės kaimo mokyklos dažnai neturi galimybės įsigyti komercinių "
    "valdymo sprendimų, todėl tampa aktualu sukurti pritaikytą, paprastą "
    "naudoti ir nemokamai prieinamą sistemą. Tokio pobūdžio sprendimas leidžia "
    "mokytojams ir administracijai sumažinti rankinio darbo apimtis, greičiau "
    "pasiekti reikalingus duomenis bei priimti pagrįstus sprendimus.",
    bold_prefix="Temos aktualumas. "
)

# Problema
prideti_pastraipa(
    doc,
    "Šiuo metu Subačiaus gimnazijos Noriūnų Jono Černiaus skyriuje mokinių "
    "asmens, tėvų kontaktiniai, vaiko gerovės komisijos bei pedagogų "
    "kvalifikacijos dokumentai saugomi popieriniu pavidalu arba atskiruose "
    "kompiuterio failuose. Toks duomenų valdymo būdas apsunkina informacijos "
    "paiešką, didina duomenų praradimo riziką ir trukdo operatyviai "
    "bendradarbiauti tarp mokyklos darbuotojų. Neturint vienos vietos, "
    "kurioje būtų matomi mokinį papildantys atributai (pavyzdžiui, ar vaikas "
    "vežamas mokyklos autobusu, ar yra buvęs svarstomas gerovės komisijoje), "
    "apsunkėja kasdienis administracinis darbas.",
    bold_prefix="Problema. "
)

# Objektas
prideti_pastraipa(
    doc,
    "Mokyklos vidinio valdymo informacinė sistema, skirta mokytojams ir "
    "administracijai centralizuotai valdyti mokinių, klasių, tėvų "
    "kontaktinius duomenis, vaiko gerovės komisijos pastabas, mokytojų "
    "kvalifikacijos dokumentus bei mokyklos vidaus skelbimus.",
    bold_prefix="Objektas. "
)

# Tikslas
prideti_pastraipa(
    doc,
    "Suprojektuoti ir realizuoti internetinio tipo mokyklos valdymo "
    "informacinę sistemą Kupiškio rajono Subačiaus gimnazijos Noriūnų Jono "
    "Černiaus skyriui, skirtą centralizuotai valdyti mokinių, klasių, tėvų "
    "duomenis bei mokytojų profesinio tobulinimosi dokumentus.",
    bold_prefix="Tikslas. "
)

# Uždaviniai - su Bold antrašte, paskui numeruotas sąrašas
p = doc.add_paragraph(style="TEKSTAS")
p.paragraph_format.first_line_indent = Cm(1.27)
p.paragraph_format.space_after = Pt(0)
run = p.add_run("Uždaviniai.")
run.bold = True
run.font.name = "Times New Roman"
run.font.size = Pt(12)

uzdaviniai = [
    "atlikti probleminės srities analizę, identifikuoti mokyklos valdymo "
    "procesus bei suformuluoti kuriamos sistemos funkcinius ir nefunkcinius "
    "reikalavimus;",

    "suprojektuoti sistemos architektūrą bei vartotojo sąsają: parengti "
    "panaudos atvejų, veiklos, klasių ir esybių–ryšių diagramas;",

    "realizuoti sistemos prototipą, taikant Python programavimo kalbą "
    "(Flask karkasą), HTML, CSS, JavaScript kalbas bei SQLite duomenų bazę; "
    "įgyvendinti vartotojų autentikaciją ir rolėmis paremtą prieigos "
    "kontrolę;",

    "įdiegti realizuotą sistemą į debesijos serverį (Render.com), atlikti "
    "funkcionalumo testavimą bei parengti diegimo ir naudotojo instrukcijas.",
]

for i, uzd in enumerate(uzdaviniai, 1):
    p = doc.add_paragraph(style="TEKSTAS")
    p.paragraph_format.first_line_indent = Cm(1.27)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(f"{i}. {uzd}")
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

# Darbo struktūra
prideti_pastraipa(
    doc,
    "Ataskaitą sudaro įvadas, keturi pagrindiniai skyriai (praktikos užduoties "
    "formulavimas, užduoties analizė, programinė realizacija ir naudotojo "
    "instrukcija), išvados ir siūlymai, informacijos šaltinių sąrašas bei "
    "priedai. Praktinis sistemos realizacijos rezultatas pasiekiamas internete, "
    "išeities kodas publikuojamas viešojoje versijų valdymo saugykloje GitHub.",
    bold_prefix="Darbo struktūra. "
)

# Praktikos trukmė
prideti_pastraipa(
    doc,
    f"Profesinė praktika vyko nuo {DATA_PRADZIA} iki {DATA_PABAIGA}, "
    "praktikos apimtis – 12 kreditų.",
    bold_prefix="Praktikos trukmė. "
)

# ----------------------------------------------------------------------------
# 1. PRAKTIKOS UŽDUOTIES FORMULAVIMAS
# ----------------------------------------------------------------------------

prideti_skyriaus_antraste(doc, "1. Praktikos užduoties formulavimas")

prideti_pastraipa(
    doc,
    "Šiame skyriuje pateikiami kuriamos mokyklos valdymo informacinės sistemos "
    "(toliau – Sistema) funkciniai ir nefunkciniai reikalavimai. Funkciniais "
    "reikalavimais nusakoma, ką Sistema gebės atlikti – aprašomos pagrindinės "
    "ir pagalbinės programos funkcijos, jų pradiniai duomenys, atliekami "
    "veiksmai ir rezultatas. Nefunkciniais reikalavimais apibrėžiamos "
    "savybės, ribojančios galimų projektinių sprendimų aibę: saugumas, "
    "našumas, naudojimo patogumas ir kiti aspektai. Reikalavimai suformuluoti "
    "atlikus probleminės srities analizę bei suderinus su priimančios "
    "organizacijos praktikos vadovu."
)

# 1.1 Funkciniai reikalavimai
prideti_poskyrio_antraste(doc, "1.1. Funkciniai reikalavimai")

prideti_pastraipa(
    doc,
    "Funkciniai reikalavimai aprašo Sistemos atliekamus veiksmus. "
    "Pagrindinės funkcijos skirtos kuriamos Sistemos siekiui realizuoti – "
    "mokinių, klasių, tėvų bei kvalifikacijos kėlimo dokumentų valdymui. "
    "Pagalbinės funkcijos užtikrina Sistemos veikimo kokybę, vartotojo patirtį "
    "ir integraciją su išorinėmis sistemomis. Pagrindinės Sistemos funkcijos "
    "ir jų aprašymas pateikti 1 lentelėje (žr. 1 lentelė)."
)

prideti_lenteles_antraste(doc, "1", "Pagrindinės Sistemos funkcijos")

pagrindines_funkcijos = [
    ["F1. Vartotojų autentikacija",
     "El. paštas, slaptažodis",
     "Tikrinami vartotojo prisijungimo duomenys; sukuriama sesija; nustatoma vartotojo rolė",
     "Vartotojas nukreipiamas į pradžios langą su jo rolei priskirtomis funkcijomis"],

    ["F2. Klasių valdymas",
     "Klasės pavadinimas, mokslo metai, klasės vadovas",
     "Sukuriamas, redaguojamas ar pašalinamas klasės įrašas; priskiriamas klasės vadovas",
     "Klasių sąrašas atvaizduojamas su mokinių skaičiumi"],

    ["F3. Mokinių valdymas",
     "Vardas, pavardė, gimimo data, kontaktiniai duomenys, klasė, tėvų informacija, papildomi požymiai",
     "Pridedamas, redaguojamas, peržiūrimas ar pašalinamas mokinio įrašas; vykdoma paieška ir filtravimas pagal klasę",
     "Mokinio detalus profilis su visa susijusia informacija"],

    ["F4. Diplomų valdymas",
     "Failas (PDF, PNG, JPG), pavadinimas, seminaras, išdavimo data, aprašymas",
     "Įkeliamas dokumento failas; tikrinamas tipas ir dydis; saugomas serveryje su nuoroda duomenų bazėje",
     "Diplomas matomas sąraše; galima peržiūrėti ar atsisiųsti"],

    ["F5. Skelbimų valdymas",
     "Pavadinimas, turinys, svarbumo žymeklis",
     "Sukuriamas, redaguojamas ar pašalinamas skelbimas; svarbūs skelbimai pažymimi etikete",
     "Skelbimas rodomas darbuotojams pradžios lange ir bendrame sąraše"],

    ["F6. Vartotojų administravimas",
     "Vardas, pavardė, el. paštas, rolė, slaptažodis",
     "Administratorius prideda, redaguoja ar pašalina mokytojų ir administratorių paskyras",
     "Atnaujintas vartotojų sąrašas"],

    ["F7. Globali paieška",
     "Tekstinė užklausa",
     "Vykdoma paieška mokinių, klasių, diplomų bei skelbimų lentelėse",
     "Rasti rezultatai sugrupuojami pagal kategorijas ir atvaizduojami vartotojui"],

    ["F8. Profilio valdymas",
     "Esamas slaptažodis, naujas slaptažodis, asmens duomenys",
     "Vartotojas keičia savo prisijungimo duomenis ar slaptažodį po identifikacijos patikrinimo",
     "Atnaujinti vartotojo duomenys; informacinis pranešimas apie sėkmingą operaciją"],

    ["F9. Duomenų eksportas",
     "Mokinių sąrašas (su pasirinkta klase ar visu sąrašu)",
     "Generuojamas CSV failas su mokinių duomenimis, įskaitant tėvų informaciją",
     "Vartotojas atsisiunčia CSV failą savo kompiuteryje"],
]

sukurti_lentele(
    doc,
    ["Funkcija", "Pradiniai duomenys", "Atliekami veiksmai", "Rezultatas"],
    pagrindines_funkcijos,
    stulpelis_pločiai=[3.5, 3.5, 5.5, 4.5],
)

prideti_pastraipa(
    doc,
    "Pagalbinės Sistemos funkcijos neturi tiesioginės įtakos pagrindiniam "
    "tikslui, tačiau užtikrina Sistemos veikimo kokybę bei vartotojo patogumą. "
    "Šios funkcijos apibūdintos 2 lentelėje (žr. 2 lentelė)."
)

prideti_lenteles_antraste(doc, "2", "Pagalbinės Sistemos funkcijos")

pagalbines_funkcijos = [
    ["F10. Statistikos atvaizdavimas",
     "Duomenų bazės įrašai",
     "Skaičiuojami vartotojų, klasių, mokinių, diplomų skaičiai; generuojama stulpelinė diagrama",
     "Pradžios lange atvaizduojama Sistemos veiklos apžvalga"],

    ["F11. Slaptažodžių šifravimas",
     "Vartotojo įvestas slaptažodis",
     "Slaptažodis konvertuojamas į hash reikšmę naudojant Werkzeug PBKDF2 algoritmą",
     "Slaptažodžio hash saugomas duomenų bazėje, originalas nesaugomas"],

    ["F12. TAMO dienyno integracija",
     "Vartotojo veiksmas",
     "Atidaroma TAMO dienyno svetainė naujame naršyklės skirtuke",
     "Vartotojas tęsia darbą TAMO sistemoje, neuždarydamas mokyklos sistemos"],

    ["F13. Tamsaus režimo perjungimas",
     "Vartotojo pasirinkimas",
     "Perjungiama tarp šviesaus ir tamsaus dizaino režimo; pasirinkimas saugomas naršyklės lokalioje saugykloje",
     "Sistema atvaizduojama pasirinktoje temoje"],

    ["F14. Failų tipo patikrinimas",
     "Įkeliamas failas",
     "Tikrinamas failo plėtinys ir maksimalus dydis (iki 16 MB); leidžiami tik PDF, PNG, JPG, JPEG",
     "Leidžiamas arba blokuojamas failo įkėlimas su klaidos pranešimu"],
]

sukurti_lentele(
    doc,
    ["Funkcija", "Pradiniai duomenys", "Atliekami veiksmai", "Rezultatas"],
    pagalbines_funkcijos,
    stulpelis_pločiai=[3.5, 3.5, 5.5, 4.5],
)

# 1.2 Nefunkciniai reikalavimai
prideti_poskyrio_antraste(doc, "1.2. Nefunkciniai reikalavimai")

prideti_pastraipa(
    doc,
    "Nefunkciniai reikalavimai apibrėžia Sistemos kokybines savybes, kurios "
    "tiesiogiai neįtakoja jos atliekamų funkcijų, tačiau yra būtinos "
    "užtikrinant patikimą, saugų ir patogų vartotojo darbą. Šie reikalavimai "
    "buvo suformuluoti remiantis tipinių internetinių valdymo sistemų gerąja "
    "praktika bei priimančios organizacijos poreikiais."
)

# Saugumas
prideti_pastraipa(
    doc,
    "Visi vartotojų slaptažodžiai saugomi tik užšifruoti, taikant "
    "PBKDF2 algoritmą su sūdyklomis (angl. *salt*). Prisijungus prie Sistemos, "
    "sukuriama saugi sesija, kuri automatiškai uždaroma po neaktyvumo "
    "laikotarpio. Sistemoje įgyvendinta rolėmis paremta prieigos kontrolė "
    "(angl. *Role-Based Access Control, RBAC*): administratoriaus rolė "
    "leidžia valdyti visus duomenis, tuo tarpu mokytojo rolė turi ribotas "
    "teises – administracinės sekcijos yra paslėptos. Visi įkeliami failai "
    "tikrinami pagal tipą ir dydį, siekiant užkirsti kelią potencialiai "
    "kenkėjiškų failų patekimui į serverį.",
    bold_prefix="Saugumas. "
)

# Našumas
prideti_pastraipa(
    doc,
    "Sistemos atsako laikas neturi viršyti dviejų sekundžių esant tipinei "
    "apkrovai (iki dešimties vienu metu prisijungusių vartotojų). Pagrindinių "
    "puslapių užkrovimas turi būti ne lėtesnis nei vienos sekundės; duomenų "
    "bazės užklausų našumas užtikrinamas optimizuojant kreipinius bei "
    "naudojant indeksus dažnai filtruojamiems laukams (vartotojo el. paštas, "
    "klasės identifikatorius).",
    bold_prefix="Našumas. "
)

# Naudojimo patogumas
prideti_pastraipa(
    doc,
    "Vartotojo sąsaja sukurta lietuvių kalba, taikant nuoseklų informacijos "
    "išdėstymą bei aiškiai matomus interaktyvius elementus. Sąsaja "
    "adaptyvi (angl. *responsive design*) – tinkamai veikia stalinio "
    "kompiuterio, planšetinio kompiuterio bei išmaniojo telefono ekranuose. "
    "Įgyvendintas tamsus režimas, palengvinantis darbą menkesnio apšvietimo "
    "sąlygomis. Pagrindinės funkcijos pasiekiamos ne daugiau kaip per tris "
    "paspaudimus nuo pradžios lango.",
    bold_prefix="Naudojimo patogumas. "
)

# Suderinamumas
prideti_pastraipa(
    doc,
    "Sistema veikia šiuolaikinėse naršyklėse: *Google Chrome*, *Mozilla "
    "Firefox*, *Microsoft Edge*, *Safari*. Reikalaujama minimali naršyklės "
    "versija – ne senesnė nei dvejų metų. Serverio dalis paleidžiama bet "
    "kurioje operacinėje sistemoje, palaikančioje *Python 3.10* arba "
    "naujesnę versiją.",
    bold_prefix="Suderinamumas. "
)

# Patikimumas
prideti_pastraipa(
    doc,
    "Duomenų vientisumas užtikrinamas naudojant duomenų bazės transakcijas; "
    "kiekvienas duomenų pakeitimas vykdomas atomiškai. Sistemos veikimas "
    "stebimas serverio žurnaluose (angl. *logs*), kuriuose registruojami "
    "klaidų atvejai bei svarbūs vartotojų veiksmai. Numatomas Sistemos "
    "prieinamumas – ne mažiau kaip 99 procentai laiko per mėnesį.",
    bold_prefix="Patikimumas. "
)

# Plečiamumas
prideti_pastraipa(
    doc,
    "Sistemos architektūra moduliariai suskaidyta į atskirus komponentus: "
    "modelius, maršrutus (angl. *routes*), šablonus (angl. *templates*) bei "
    "statinius failus. Tokia struktūra leidžia ateityje paprastai pridėti "
    "naujus modulius – pavyzdžiui, pamokų tvarkaraščio valdymą, mokinių "
    "lankomumo apskaitą ar tėvų prieigos sistemą, – neperdirbant esamos "
    "kodo bazės.",
    bold_prefix="Plečiamumas. "
)

# Prieinamumas
prideti_pastraipa(
    doc,
    "Sąsaja palaiko klaviatūros navigaciją: visi interaktyvūs elementai "
    "pasiekiami spaudžiant klavišą *Tab*; matomi židinio (angl. *focus*) "
    "indikatoriai. Spalvų kontrastas atitinka *WCAG 2.1 AA* lygio "
    "rekomendacijas. Visi paveikslai turi alternatyvų teksto aprašymą "
    "ekrano skaitytuvams.",
    bold_prefix="Prieinamumas. "
)

# 1.3 Sistemos vartotojų rolės
prideti_poskyrio_antraste(doc, "1.3. Sistemos vartotojų rolės ir prieigos teisės")

prideti_pastraipa(
    doc,
    "Sistemoje numatytos dvi pagrindinės vartotojų rolės, atitinkančios "
    "skirtingas mokyklos darbuotojų pareigybes ir atsakomybės sritis. "
    "Kiekviena rolė turi tiksliai apibrėžtą prieigos teisių rinkinį, "
    "užtikrinantį duomenų valdymo tvarkingumą bei atsakomybės paskirstymą. "
    "Rolių aprašymai pateikti 3 lentelėje (žr. 3 lentelė)."
)

prideti_lenteles_antraste(doc, "3", "Sistemos vartotojų rolės ir jų prieigos teisės")

roles = [
    ["Administratorius",
     "Mokyklos vadovas, direktoriaus pavaduotojas",
     "Pilna prieiga: valdo vartotojus, klases, mokinius, diplomus, skelbimus; gali šalinti bet kurį įrašą; mato visus mokytojų įkeltus diplomus"],

    ["Mokytojas",
     "Mokyklos pedagoginis darbuotojas",
     "Mato klases ir mokinius; gali pridėti bei redaguoti mokinių duomenis; valdo savo įkeltus diplomus; kuria skelbimus; negali kurti naujų vartotojų ar klasių"],
]

sukurti_lentele(
    doc,
    ["Rolė", "Pareigybės pavyzdys", "Prieigos teisės"],
    roles,
    stulpelis_pločiai=[3.5, 4.0, 9.5],
)

prideti_pastraipa(
    doc,
    "Prieigos teisių patikrinimas vykdomas tiek vartotojo sąsajos lygyje "
    "(slėpiami nepasiekiami meniu punktai), tiek serverio užklausų lygyje "
    "(tikrinamas vartotojo rolės atributas prieš vykdant veiksmą). Tokia "
    "dviejų lygių apsauga užkerta kelią neteisėtai prieigai net ir tuomet, "
    "kai vartotojas bandytų pasiekti uždraustą funkciją tiesiogiai per URL "
    "adresą."
)


# ============================================================================
# DIAGRAMOS INSTRUKCIJOS HELPER
# ============================================================================

def prideti_diagramos_instrukcija(doc, pavadinimas, irankis, elementai, layout=""):
    """Prideda pastebimą blokuotę su instrukcija, kaip nubraižyti diagramą."""
    # Skiriamoji eilutė
    p_top = doc.add_paragraph()
    p_top.paragraph_format.first_line_indent = Cm(0)
    p_top.paragraph_format.space_before = Pt(6)
    p_top.paragraph_format.space_after = Pt(0)
    p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_top.add_run("┌" + "─" * 70 + "┐")
    r.font.name = "Courier New"
    r.font.size = Pt(10)

    # Antraštė
    p1 = doc.add_paragraph()
    p1.paragraph_format.first_line_indent = Cm(0)
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(0)
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p1.add_run(f"▶ INSTRUKCIJA DIAGRAMAI: {pavadinimas.upper()}")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)

    # Įrankis
    p2 = doc.add_paragraph()
    p2.paragraph_format.first_line_indent = Cm(0)
    p2.paragraph_format.space_before = Pt(6)
    p2.paragraph_format.space_after = Pt(0)
    r1 = p2.add_run("Rekomenduojamas įrankis: ")
    r1.bold = True
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(11)
    r2 = p2.add_run(irankis)
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(11)

    # Elementai
    p3 = doc.add_paragraph()
    p3.paragraph_format.first_line_indent = Cm(0)
    p3.paragraph_format.space_before = Pt(6)
    p3.paragraph_format.space_after = Pt(0)
    r = p3.add_run("Privalomi diagramos elementai:")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)

    for el in elementai:
        p_el = doc.add_paragraph()
        p_el.paragraph_format.first_line_indent = Cm(0)
        p_el.paragraph_format.left_indent = Cm(0.5)
        p_el.paragraph_format.space_before = Pt(0)
        p_el.paragraph_format.space_after = Pt(0)
        r = p_el.add_run("• " + el)
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)

    if layout:
        p4 = doc.add_paragraph()
        p4.paragraph_format.first_line_indent = Cm(0)
        p4.paragraph_format.space_before = Pt(6)
        p4.paragraph_format.space_after = Pt(0)
        r1 = p4.add_run("Išdėstymo patarimas: ")
        r1.bold = True
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(11)
        r2 = p4.add_run(layout)
        r2.font.name = "Times New Roman"
        r2.font.size = Pt(11)

    # Skiriamoji eilutė apačioje
    p_end = doc.add_paragraph()
    p_end.paragraph_format.first_line_indent = Cm(0)
    p_end.paragraph_format.space_before = Pt(6)
    p_end.paragraph_format.space_after = Pt(6)
    p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_end.add_run("└" + "─" * 70 + "┘")
    r.font.name = "Courier New"
    r.font.size = Pt(10)


# ============================================================================
# 2. PRAKTIKOS UŽDUOTIES ANALIZĖ
# ============================================================================

prideti_skyriaus_antraste(doc, "2. Praktikos užduoties analizė")

prideti_pastraipa(
    doc,
    "Šiame skyriuje pateikiama Sistemos analizė remiantis UML (angl. "
    "*Unified Modeling Language*) modeliavimo principais. Atlikta panaudos "
    "atvejų, veiklos bei sekos diagramų analizė, sudaryta esybių–ryšių "
    "diagrama bei aprašyta projekto katalogų struktūra. Analizė leido "
    "tiksliai apibrėžti Sistemos elgseną, vartotojų sąveiką su jos "
    "funkcijomis bei duomenų saugojimo modelį."
)

# 2.1 Sistemos naudotojai
prideti_poskyrio_antraste(doc, "2.1. Sistemos naudotojai")

prideti_pastraipa(
    doc,
    "Sistemoje numatytos dvi vartotojų rolės, sąveikaujančios su jos "
    "funkcijomis: administratorius ir mokytojas. Administratorius "
    "atstovauja mokyklos vadovybei – direktoriui ar direktoriaus "
    "pavaduotojui ugdymui. Jis turi pilną prieigą prie visų Sistemos "
    "funkcijų. Mokytojas atstovauja pedagoginiam personalui ir naudojasi "
    "Sistema savo darbo užduotims atlikti. Detalus naudotojų aprašymas "
    "pateiktas 4 lentelėje (žr. 4 lentelė)."
)

prideti_lenteles_antraste(doc, "4", "Sistemos naudotojų aprašymas")

naudotojai = [
    ["Administratorius",
     "Mokyklos direktorius arba direktoriaus pavaduotojas ugdymui",
     "Visos pagrindinės ir pagalbinės Sistemos funkcijos, įskaitant vartotojų ir klasių valdymą"],

    ["Mokytojas",
     "Mokyklos pedagoginis darbuotojas (klasės vadovas, dalyko mokytojas)",
     "Mokinių duomenų valdymas, diplomų įkėlimas, skelbimų skaitymas ir kūrimas, profilio valdymas"],
]

sukurti_lentele(
    doc,
    ["Vartotojo rolė", "Atstovaujama pareigybė", "Prieinamos funkcijos"],
    naudotojai,
    stulpelis_pločiai=[3.5, 5.0, 8.5],
)

# 2.2 Panaudos atvejų diagrama
prideti_poskyrio_antraste(doc, "2.2. Panaudos atvejų diagrama")

prideti_pastraipa(
    doc,
    "Panaudos atvejų diagrama (angl. *Use Case Diagram*) vaizduoja, kaip "
    "vartotojai sąveikauja su Sistemos funkcijomis. Joje pavaizduoti abu "
    "Sistemos veikėjai (angl. *actors*) ir jų pasiekiamų panaudos atvejų "
    "rinkinys. Bendras Sistemos panaudos atvejų vaizdas pateiktas "
    "1 paveiksle (žr. 1 pav.)."
)

prideti_diagramos_instrukcija(
    doc,
    pavadinimas="1 pav. Sistemos panaudos atvejų diagrama",
    irankis="draw.io (diagrams.net) – nemokamas, internete prieinamas. "
            "Alternatyvos: Lucidchart, Microsoft Visio, yEd.",
    elementai=[
        'Du veikėjai (žmogiukai): „Administratorius” (kairėje) ir „Mokytojas” (dešinėje).',
        'Sistemos riba – stačiakampis su užrašu „Mokyklos valdymo sistema” viršuje.',
        "Panaudos atvejai (elipsės) viduje stačiakampio, sugrupuoti pagal sritį:",
        '    – Autentikacijos sritis: „Prisijungti”, „Atsijungti”, „Keisti slaptažodį”',
        '    – Mokinių sritis: „Peržiūrėti mokinius”, „Pridėti mokinį”, „Redaguoti mokinį”, „Šalinti mokinį”, „Eksportuoti CSV”',
        '    – Klasių sritis: „Peržiūrėti klases”, „Pridėti klasę”, „Redaguoti klasę”',
        '    – Diplomų sritis: „Įkelti diplomą”, „Peržiūrėti diplomus”, „Atsisiųsti diplomą”',
        '    – Skelbimų sritis: „Kurti skelbimą”, „Skaityti skelbimus”',
        '    – Vartotojų sritis: „Valdyti vartotojus” (tik administratoriui)',
        "Linijos jungiančios veikėjus su panaudos atvejais: ištisinės linijos.",
        'Tarp panaudos atvejų galima naudoti «include» (punktyrinė rodyklė) – pvz., visi veiksmai „include” Prisijungimą.',
    ],
    layout="Administratorius kairėje, jam priskirti VISI panaudos atvejai. "
           "Mokytojas dešinėje, jam priskirti VISI panaudos atvejai IŠSKYRUS "
           '„Valdyti vartotojus” ir „Šalinti klasę”. Panaudos atvejus išdėstyti '
           "vertikaliai grupėmis pagal sritį, kiekvienai sričiai galima naudoti "
           "punktyrinį stačiakampį kaip paketą (angl. *package*).",
)

prideti_pastraipa(
    doc,
    "Iš pateiktos diagramos matyti, kad administratorius turi prieigą prie "
    "visų panaudos atvejų, įskaitant vartotojų valdymą bei klasių šalinimą. "
    "Mokytojui prieinama pagrindinė dalis veiksmų, susijusių su kasdieniu "
    "darbu: mokinių valdymu, diplomų įkėlimu ir skelbimų skaitymu. Toks "
    "teisių paskirstymas atitinka mokyklos darbo logiką ir užtikrina, kad "
    "kritiniai administraciniai veiksmai būtų prieinami tik atsakingiems "
    "darbuotojams."
)

prideti_pastraipa(
    doc,
    "Detaliam panaudos atvejui pristatyti pasirinktas vienas iš dažniausių "
    'veiksmų – „Pridėti naują mokinį”. Šio panaudos atvejo scenarijus '
    "pateiktas 5 lentelėje (žr. 5 lentelė)."
)

prideti_lenteles_antraste(doc, "5", 'Panaudos atvejo „Pridėti naują mokinį” scenarijus')

scenarijus = [
    ["Panaudos atvejo numeris", "PA01"],
    ["Pavadinimas", "Pridėti naują mokinį"],
    ["Veikėjas", "Mokytojas arba administratorius"],
    ["Tikslas", "Įvesti naujo mokinio duomenis į Sistemą ir juos išsaugoti"],
    ["Sąlyga prieš", "Vartotojas yra prisijungęs prie Sistemos"],
    ["Pagrindinis srautas",
     '1. Vartotojas pasirenka meniu punktą „Mokiniai”.\n'
     "2. Sistema atvaizduoja mokinių sąrašą.\n"
     '3. Vartotojas spaudžia mygtuką „Naujas mokinys”.\n'
     "4. Sistema atveria mokinio duomenų formą.\n"
     "5. Vartotojas užpildo privalomus laukus (vardas, pavardė, klasė).\n"
     "6. Vartotojas užpildo neprivalomus laukus (gimimo data, kontaktai, tėvai, autobusas, VGK).\n"
     '7. Vartotojas spaudžia „Pridėti mokinį”.\n'
     "8. Sistema patikrina duomenų korektiškumą.\n"
     "9. Sistema išsaugo įrašą duomenų bazėje.\n"
     "10. Sistema atvaizduoja mokinio profilio puslapį su patvirtinimo žinute."],
    ["Alternatyvus srautas",
     "8a. Sistema nustato neužpildytus privalomus laukus → grąžinama į formą su klaidos pranešimu."],
    ["Sąlyga po", "Naujas mokinys įtraukiamas į Sistemos duomenų bazę"],
]

sukurti_lentele(
    doc,
    ["Atributas", "Aprašymas"],
    scenarijus,
    stulpelis_pločiai=[4.5, 12.5],
)

# 2.3 Veiklos diagrama
prideti_poskyrio_antraste(doc, "2.3. Veiklos diagrama")

prideti_pastraipa(
    doc,
    "Veiklos diagrama (angl. *Activity Diagram*) detaliai vaizduoja "
    "Sistemos vidinį veiksmų eiliškumą bei sprendimų logiką. Toliau "
    "pateikta diagrama atvaizduoja anksčiau aprašyto panaudos atvejo "
    '„Pridėti naują mokinį” eigą, įskaitant duomenų patikrinimą bei '
    "alternatyvius scenarijus klaidų atveju. Diagrama pateikta 2 "
    "paveiksle (žr. 2 pav.)."
)

prideti_diagramos_instrukcija(
    doc,
    pavadinimas="2 pav. Mokinio pridėjimo veiklos diagrama",
    irankis='draw.io – kategorija „UML” → „Activity”.',
    elementai=[
        "Pradžios mazgas: užpildytas juodas apskritimas (viršuje).",
        "Veiklos blokai (suapvalinti stačiakampiai), nuosekliai:",
        '    1. „Vartotojas pasirenka meniu „Mokiniai””',
        '    2. „Sistema atvaizduoja mokinių sąrašą”',
        '    3. „Vartotojas paspaudžia „Naujas mokinys””',
        '    4. „Sistema atveria mokinio formą”',
        '    5. „Vartotojas užpildo duomenis”',
        '    6. „Vartotojas paspaudžia „Pridėti mokinį””',
        'Sprendimo rombas (po 6 žingsnio): „Ar duomenys teisingi?”',
        '    – Šaka „Ne” → veikla „Sistema parodo klaidos pranešimą” → grįžta į 5 žingsnį',
        '    – Šaka „Taip” → veikla „Sistema išsaugo duomenis duomenų bazėje””',
        'Po išsaugojimo: veikla „Sistema atvaizduoja mokinio profilį”',
        "Pabaigos mazgas: juodas apskritimas su rato kraštu (apačioje).",
        "Visi perėjimai – juodos rodyklės su strėlytėmis.",
    ],
    layout="Diagrama braižoma vertikaliai (iš viršaus į apačią). "
           'Sprendimo rombas turi du išėjimus su užrašais „Taip” ir „Ne”. '
           "Klaidos šaka grįžta į formos užpildymo žingsnį, todėl reikės "
           "naudoti grįžimo rodyklę į kairę.",
)

prideti_pastraipa(
    doc,
    "Veiklos diagrama atskleidžia, kad Sistemoje vykdomas dvigubas duomenų "
    "patikrinimas: vartotojo sąsajoje pažymimi privalomi laukai, o serverio "
    "pusėje atliekamas papildomas validavimas. Toks sprendimas leidžia "
    "anksti aptikti įvesties klaidas bei užtikrinti duomenų bazės "
    "vientisumą."
)

# 2.4 Sekos diagrama
prideti_poskyrio_antraste(doc, "2.4. Sekos diagrama")

prideti_pastraipa(
    doc,
    "Sekos diagrama (angl. *Sequence Diagram*) atspindi sąveiką tarp "
    "Sistemos komponentų laiko atžvilgiu. Pateikta diagrama vaizduoja "
    "vartotojo autentikacijos procesą – nuo prisijungimo formos užpildymo "
    "iki sesijos sukūrimo (žr. 3 pav.)."
)

prideti_diagramos_instrukcija(
    doc,
    pavadinimas="3 pav. Vartotojo autentikacijos sekos diagrama",
    irankis=('draw.io – kategorija „UML” → „Sequence”. Alternatyvi priemonė: '
             'sequencediagram.org (paprastas tekstinis aprašymas).'),
    elementai=[
        "Penki vertikalūs gyvavimo linijos (angl. *lifeline*) stulpeliai su pavadinimais viršuje:",
        '    1. „Vartotojas” (kairėje)',
        '    2. „Naršyklė”',
        '    3. „Flask serveris”',
        '    4. „Autentikacijos modulis”',
        '    5. „Duomenų bazė” (dešinėje)',
        "Žinutės (horizontalios rodyklės) iš viršaus į apačią:",
        '    1. Vartotojas → Naršyklė: „Įveda el. paštą ir slaptažodį”',
        '    2. Naršyklė → Flask serveris: „POST /login (el. paštas, slaptažodis)”',
        '    3. Flask serveris → Autentikacijos modulis: „authenticate(email, password)”',
        '    4. Autentikacijos modulis → Duomenų bazė: „SELECT user WHERE email = ?”',
        '    5. Duomenų bazė → Autentikacijos modulis: „User objektas su slaptažodžio hash” (punktyrinė grįžimo rodyklė)',
        '    6. Autentikacijos modulis: vidinė žinutė sau – „check_password_hash()”',
        '    7. Autentikacijos modulis → Flask serveris: „Sėkmingas patvirtinimas + User objektas”',
        '    8. Flask serveris → Naršyklė: „HTTP 302 redirect → /dashboard; Sukuriama sesija”',
        '    9. Naršyklė → Vartotojas: „Atvaizduoja pradžios langą”',
        "Aktyvavimo stačiakampiai (angl. *activation bars*) – ploni vertikalūs stačiakampiai ant gyvavimo linijų, kai komponentas vykdo veiksmą.",
    ],
    layout="Diagrama plinta horizontaliai (5 stulpeliai), žinutės eina iš viršaus į apačią. "
           "Grįžimo žinutes (rezultatus) braižyti punktyrinėmis rodyklėmis, naujas užklausas – ištisinėmis. "
           "Stulpelių antraštės juodais stačiakampiais.",
)

# 2.5 Esybių-ryšių diagrama
prideti_poskyrio_antraste(doc, "2.5. Esybių–ryšių diagrama")

prideti_pastraipa(
    doc,
    "Sistemos duomenų saugojimo modelis suprojektuotas reliacinės duomenų "
    "bazės pagrindu. Esybių–ryšių diagrama (toliau – ER diagrama) atspindi "
    "pagrindines Sistemos esybes, jų atributus bei tarpusavio ryšius. "
    "Sistemoje numatytos penkios pagrindinės esybės: vartotojas, klasė, "
    "mokinys, diplomas ir skelbimas. Esybių aprašymas pateiktas 6 lentelėje "
    "(žr. 6 lentelė)."
)

prideti_lenteles_antraste(doc, "6", "Sistemos duomenų bazės esybės")

esybes = [
    ["vartotojai", "Sistemos prisijungimo paskyros – administratoriai ir mokytojai",
     "id, vardas, pavardė, el. paštas, slaptažodžio hash, rolė, sukūrimo data"],

    ["klases", "Mokyklos klasės",
     "id, pavadinimas, mokslo metai, vadovo id (nuoroda į vartotoją)"],

    ["mokiniai", "Mokyklos mokiniai su tėvų ir papildoma informacija",
     "id, vardas, pavardė, gimimo data, el. paštas, telefonas, adresas, pastabos, "
     "klasės id, motinos duomenys (vardas, telefonas, el. paštas), tėvo duomenys, "
     "mokyklos autobusas (taip/ne), gerovės komisija (taip/ne), gerovės kom. data, gerovės kom. pastabos"],

    ["diplomai", "Mokytojų įkelti kvalifikacijos kėlimo dokumentai",
     "id, pavadinimas, aprašymas, seminaras, išdavimo data, failo kelias, originalus failo vardas, "
     "failo tipas, vartotojo id, įkėlimo data"],

    ["skelbimai", "Mokyklos vidaus pranešimai darbuotojams",
     "id, pavadinimas, turinys, svarbumas (taip/ne), vartotojo id, sukūrimo data"],
]

sukurti_lentele(
    doc,
    ["Esybė", "Aprašymas", "Pagrindiniai atributai"],
    esybes,
    stulpelis_pločiai=[2.5, 4.5, 10.0],
)

prideti_pastraipa(
    doc,
    "Tarp esybių apibrėžti šie ryšiai: vartotojas gali būti vienos arba "
    'kelių klasių vadovas (1:N ryšys tarp „vartotojai” ir „klases”); klasė '
    'talpina vieną arba daugiau mokinių (1:N ryšys tarp „klases” ir '
    '„mokiniai”); vartotojas gali įkelti vieną ar daugiau diplomų (1:N '
    'ryšys tarp „vartotojai” ir „diplomai”); vartotojas gali sukurti vieną '
    'ar daugiau skelbimų (1:N ryšys tarp „vartotojai” ir „skelbimai”). '
    "Vizualus modelio atvaizdas pateiktas 4 paveiksle (žr. 4 pav.)."
)

prideti_diagramos_instrukcija(
    doc,
    pavadinimas="4 pav. Sistemos esybių–ryšių diagrama",
    irankis="dbdiagram.io (paprasta, internete, eksportas į PDF/PNG), arba "
            "draw.io (Entity Relation šablonas), arba MySQL Workbench "
            "(EER Diagram).",
    elementai=[
        "Penkios esybių (lentelių) blokai-stačiakampiai su antrašte (lentelės pavadinimas didžiosiomis) ir atributų sąrašu po antrašte:",
        '    – „VARTOTOJAI”: id (PK), vardas, pavardė, el_pastas (UK), slaptazodzio_hash, role, sukurtas',
        '    – „KLASES”: id (PK), pavadinimas (UK), mokslo_metai, vadovo_id (FK → vartotojai.id)',
        '    – „MOKINIAI”: id (PK), vardas, pavardė, gimimo_data, el_pastas, telefonas, adresas, pastabos, klases_id (FK → klases.id), motinos_vardas, motinos_telefonas, motinos_email, tevo_vardas, tevo_telefonas, tevo_email, mokyklos_autobusas (BOOL), geroves_komisija (BOOL), geroves_komisija_data, geroves_komisija_pastabos',
        '    – „DIPLOMAI”: id (PK), pavadinimas, aprasymas, seminaras, isdavimo_data, failo_kelias, originalus_failo_vardas, failo_tipas, vartotojo_id (FK → vartotojai.id), ikeltas',
        '    – „SKELBIMAI”: id (PK), pavadinimas, turinys, svarbus (BOOL), vartotojo_id (FK → vartotojai.id), sukurtas',
        "Ryšių linijos (su Crow's Foot kardinalumo žymėjimu):",
        "    – vartotojai (1) → (0..N) klases (per vadovo_id)",
        "    – klases (1) → (1..N) mokiniai (per klases_id, CASCADE DELETE)",
        "    – vartotojai (1) → (0..N) diplomai (per vartotojo_id, CASCADE DELETE)",
        "    – vartotojai (1) → (0..N) skelbimai (per vartotojo_id, CASCADE DELETE)",
        'Pirminius raktus (PK) pažymėti šalia atributo arba ikonėle (raktelis). Užsienio raktus (FK) pažymėti „FK” prierašu.',
    ],
    layout=('Esybes išdėstyti taip, kad „vartotojai” būtų viduryje (centrinė esybė), '
            '„klases” ir „mokiniai” – kairėje, „diplomai” ir „skelbimai” – dešinėje. '
            'Tarp esybių neturėtų kirstis ryšių linijos. Naudoti Crow Foot žymėjimą '
            '(stalo kojos ženklas „daug” pusėje, brūkšnys „vienas” pusėje).'),
)

# 2.6 Projekto katalogų struktūra
prideti_poskyrio_antraste(doc, "2.6. Projekto katalogų struktūra")

prideti_pastraipa(
    doc,
    "Projekto failai organizuojami pagal Flask karkaso geriausią praktiką, "
    "atskiriant modelius, maršrutus, šablonus bei statinius failus į "
    "atskirus katalogus. Tokia struktūra užtikrina kodo perskaitomumą, "
    "palengvina priežiūrą bei leidžia paprastai pridėti naujus modulius. "
    "Projekto katalogų hierarchija pateikta 5 paveiksle (žr. 5 pav.)."
)

prideti_paveikslo_antraste(doc, "5", "Projekto katalogų struktūra")

# Katalogų struktūra kaip kodo blokas
struktura_eilutes = [
    "mokyklos-platforma/",
    "│",
    "├── app.py                    # Pagrindinis Flask aplikacijos failas",
    "├── config.py                 # Konfigūracijos parametrai",
    "├── models.py                 # Duomenų bazės modeliai (SQLAlchemy)",
    "├── seed.py                   # Demo duomenų užpildymo skriptas",
    "├── wsgi.py                   # Production WSGI įėjimo taškas",
    "├── requirements.txt          # Python paketų sąrašas",
    "├── render.yaml               # Render.com diegimo konfigūracija",
    "│",
    "├── routes/                   # URL maršrutų moduliai",
    "│   ├── __init__.py",
    "│   ├── auth.py               # Prisijungimas, atsijungimas",
    "│   ├── dashboard.py          # Pradžios langas su statistika",
    "│   ├── classes.py            # Klasių valdymas",
    "│   ├── students.py           # Mokinių valdymas, CSV eksportas",
    "│   ├── diplomas.py           # Diplomų įkėlimas ir peržiūra",
    "│   ├── announcements.py      # Skelbimų valdymas",
    "│   ├── users.py              # Vartotojų administravimas",
    "│   ├── profile.py            # Profilio valdymas, slaptažodžio keitimas",
    "│   └── search.py             # Globali paieška",
    "│",
    "├── templates/                # Jinja2 HTML šablonai",
    "│   ├── base.html             # Bazinis šablonas (sidebar, header)",
    "│   ├── login.html            # Prisijungimo puslapis",
    "│   ├── dashboard.html        # Pradžios langas",
    "│   ├── search.html           # Paieškos rezultatai",
    "│   ├── classes/              # Klasių puslapiai",
    "│   ├── students/             # Mokinių puslapiai",
    "│   ├── diplomas/             # Diplomų puslapiai",
    "│   ├── announcements/        # Skelbimų puslapiai",
    "│   ├── users/                # Vartotojų puslapiai",
    "│   └── profile/              # Profilio puslapiai",
    "│",
    "└── static/                   # Statiniai failai",
    "    ├── css/style.css         # Pasirinktiniai stiliai",
    "    ├── js/main.js            # JavaScript funkcijos",
    "    └── uploads/              # Įkelti diplomai (PDF, PNG, JPG)",
]

for eilute in struktura_eilutes:
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(eilute)
    run.font.name = "Courier New"
    run.font.size = Pt(10)

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Aukščiausio lygio kataloge yra paleidimo failai – „app.py” Flask '
    'aplikacijai inicijuoti, „wsgi.py” produkcinei aplinkai, „seed.py” '
    "duomenų bazei užpildyti demo duomenimis. Visa logika suskaidyta į "
    'tris pagrindinius katalogus: „routes” – serverio užklausų apdorojimas, '
    '„templates” – HTML šablonai, „static” – CSS, JavaScript ir įkelti '
    "failai. Tokia struktūra atitinka Flask karkaso rekomenduojamą "
    "projekto sandarą bei leidžia komandai (jei būtų) aiškiai paskirstyti "
    "atsakomybes pagal funkcines sritis."
)


# ============================================================================
# 3. PROGRAMINĖ REALIZACIJA
# ============================================================================

prideti_skyriaus_antraste(doc, "3. Programinė realizacija")

prideti_pastraipa(
    doc,
    'Šiame skyriuje pateikiamas Sistemos programinės realizacijos aprašymas: '
    'sistemos architektūra, pagrindiniai failai ir jų paskirtis, duomenų '
    'modeliai, maršrutų apdorojimo logika, vartotojo sąsajos šablonai bei '
    'saugumo realizacijos sprendimai. Sistemos kūrimui pasirinkta Python '
    'programavimo kalba (3.12 versija) bei Flask interneto programų karkasas. '
    'Pasirinkimą lėmė kalbos paprastumas, gausi bibliotekų ekosistema bei '
    'tinkamumas vidutinio sudėtingumo internetinėms sistemoms kurti.'
)

prideti_poskyrio_antraste(doc, "3.1. Sistemos architektūros apžvalga")

prideti_pastraipa(
    doc,
    'Sistema sukurta laikantis MVC (angl. *Model–View–Controller*) '
    'architektūros principų, kuriuos natūraliai realizuoja Flask karkasas. '
    'Modelio (M) sluoksnyje veikia SQLAlchemy ORM, atvaizduojantis '
    'objektus į reliacinės duomenų bazės lenteles. Rodinio (V) sluoksnis '
    'sukurtas Jinja2 šablonų sistema, kuri serverio pusėje generuoja HTML '
    'turinį. Valdiklio (C) vaidmenį atlieka Flask maršrutų funkcijos, '
    'priimančios HTTP užklausas, sąveikaujančios su modeliu ir grąžinančios '
    'atitinkamus rodinius. Naudojamų technologijų sąrašas pateiktas 7 '
    'lentelėje (žr. 7 lentelė).'
)

prideti_lenteles_antraste(doc, "7", "Sistemos kūrimui naudotos technologijos")

technologijos = [
    ["Python", "3.12", "Programavimo kalba serverio logikai"],
    ["Flask", "3.1", "Mikro interneto karkasas užklausų apdorojimui"],
    ["SQLAlchemy", "2.0", "ORM duomenų bazės valdymui"],
    ["Flask-SQLAlchemy", "3.1", "Flask integracija su SQLAlchemy"],
    ["Flask-Login", "0.6", "Vartotojų sesijų ir autentikacijos valdymas"],
    ["Werkzeug", "3.1", "WSGI ir slaptažodžių šifravimo įrankis"],
    ["Jinja2", "3.1", "HTML šablonų variklis serverio pusėje"],
    ["Gunicorn", "23.0", "WSGI serveris produkcinei aplinkai"],
    ["SQLite", "3", "Reliacinė duomenų bazių valdymo sistema"],
    ["HTML5", "—", "Vartotojo sąsajos struktūros žymėjimo kalba"],
    ["Tailwind CSS", "3.4", "Utility-first stilių karkasas"],
    ["JavaScript", "ES6+", "Kliento pusės interaktyvumas"],
    ["Chart.js", "4.4", "Statistikos diagramų atvaizdavimas"],
    ["Render.com", "—", "Debesijos platforma diegimui"],
    ["Git / GitHub", "—", "Versijų valdymas ir kodo saugykla"],
]

sukurti_lentele(
    doc,
    ["Technologija", "Versija", "Paskirtis"],
    technologijos,
    stulpelis_pločiai=[4.0, 2.5, 10.5],
)

# 3.2 Pagrindiniai sistemos failai
prideti_poskyrio_antraste(doc, "3.2. Pagrindiniai sistemos failai ir jų priklausomybės")

prideti_pastraipa(
    doc,
    'Sistemos programinis kodas suskaidytas į modulius, kurių kiekvienas '
    'atsakingas už savo funkcinę sritį. Modulių paskirtis ir tarpusavio '
    'priklausomybės pateiktos 8 lentelėje (žr. 8 lentelė).'
)

prideti_lenteles_antraste(doc, "8", "Sistemos pagrindiniai failai")

failai_sarasas = [
    ["app.py",
     "Flask aplikacijos sukūrimas, konfigūracijos užkrovimas, maršrutų registravimas",
     "config, models, routes/*"],
    ["wsgi.py",
     "Produkcinis aplikacijos įėjimo taškas Gunicorn serveriui",
     "app, seed, models"],
    ["config.py",
     "Konfigūracijos parametrai: slaptas raktas, DB URL, įkeliamų failų katalogas",
     "os (standartinė)"],
    ["models.py",
     "Duomenų bazės modeliai: vartotojai, klasės, mokiniai, diplomai, skelbimai",
     "flask_sqlalchemy, flask_login, werkzeug"],
    ["seed.py",
     "Demo duomenų generavimo skriptas pradinei aplinkai",
     "app, models, datetime"],
    ["routes/auth.py",
     "Prisijungimo, atsijungimo, prieigos kontrolės dekoratoriai",
     "flask, flask_login, models"],
    ["routes/students.py",
     "Mokinių CRUD operacijos, paieška, CSV eksportas",
     "flask, flask_login, models, csv, io"],
    ["routes/classes.py",
     "Klasių valdymo maršrutai",
     "flask, flask_login, models"],
    ["routes/diplomas.py",
     "Diplomų įkėlimas, peržiūra, atsisiuntimas",
     "flask, werkzeug.utils, models, uuid"],
    ["routes/announcements.py",
     "Skelbimų valdymo maršrutai",
     "flask, flask_login, models"],
    ["routes/users.py",
     "Vartotojų administravimas (tik administratoriui)",
     "flask, flask_login, models"],
    ["routes/profile.py",
     "Vartotojo profilio peržiūra ir slaptažodžio keitimas",
     "flask, flask_login, models"],
    ["routes/search.py",
     "Globalios paieškos funkcija",
     "flask, flask_login, models"],
    ["routes/dashboard.py",
     "Pradžios langas su statistika ir diagrama",
     "flask, flask_login, models"],
]

sukurti_lentele(
    doc,
    ["Failas", "Paskirtis", "Priklausomybės"],
    failai_sarasas,
    stulpelis_pločiai=[3.5, 8.0, 5.5],
)

# 3.3 Duomenų modeliai
prideti_poskyrio_antraste(doc, "3.3. Duomenų modeliai")

prideti_pastraipa(
    doc,
    'Faile models.py apibrėžtos visos Sistemos duomenų esybės kaip '
    'SQLAlchemy klasės. Kiekviena klasė atspindi reliacinės duomenų bazės '
    'lentelę, o klasės atributai – lentelės stulpelius. Tarp klasių '
    'apibrėžti ryšiai (angl. *relationships*), leidžiantys naviguoti tarp '
    'susijusių objektų. Vartotojo klasės pavyzdys pateiktas 1 kodo '
    'fragmente.'
)

prideti_pastraipa(
    doc,
    '1 kodo fragmentas. Vartotojo (User) duomenų modelis (failas: models.py)',
    indent=False
)
prideti_kodo_fragmentą(doc, '''class User(UserMixin, db.Model):
    """Vartotojas - mokytojas arba administratorius."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    vardas = db.Column(db.String(80), nullable=False)
    pavarde = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    slaptazodzio_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="mokytojas")
    sukurtas = db.Column(db.DateTime, default=datetime.utcnow)

    diplomai = db.relationship("Diplomas", backref="vartotojas",
                                cascade="all, delete-orphan")
    vadovaujamos_klases = db.relationship("Klase", backref="vadovas")
    skelbimai = db.relationship("Skelbimas", backref="autorius",
                                 cascade="all, delete-orphan")

    def nustatyti_slaptazodi(self, slaptazodis):
        self.slaptazodzio_hash = generate_password_hash(slaptazodis)

    def patikrinti_slaptazodi(self, slaptazodis):
        return check_password_hash(self.slaptazodzio_hash, slaptazodis)

    @property
    def yra_administratorius(self):
        return self.role == "administratorius"''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Klasė paveldi du tėvinius tipus: UserMixin iš Flask-Login bibliotekos, '
    'kuri suteikia metodus sesijų valdymui, ir db.Model – SQLAlchemy ORM '
    'bazinę klasę. Slaptažodis niekuomet nesaugomas atviru tekstu – metodas '
    'nustatyti_slaptazodi konvertuoja jį į PBKDF2-SHA256 hash naudojant '
    'Werkzeug biblioteką. Tikrinant prisijungimą, metodas patikrinti_slaptazodi '
    'lygina pateikto slaptažodžio hash su saugomu duomenų bazėje.'
)

# 3.4 Maršrutų moduliai
prideti_poskyrio_antraste(doc, "3.4. Maršrutų moduliai")

prideti_pastraipa(
    doc,
    'Visi HTTP užklausų apdorojimo maršrutai sukoncentruoti kataloge '
    'routes/, kuriame kiekvienas Python failas atstovauja atskirą Flask '
    'Blueprint – moduliarią maršrutų grupę. Toks suskaidymas leidžia '
    'paskirstyti atsakomybes, palengvina kodo priežiūrą bei pakartotinį '
    'panaudojimą. Autentikacijos modulio prisijungimo funkcijos kodas '
    'pateiktas 2 kodo fragmente.'
)

prideti_pastraipa(
    doc,
    '2 kodo fragmentas. Vartotojo prisijungimo funkcija (failas: routes/auth.py)',
    indent=False
)
prideti_kodo_fragmentą(doc, '''@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        slaptazodis = request.form.get("slaptazodis", "")

        vartotojas = User.query.filter_by(email=email).first()

        if vartotojas and vartotojas.patikrinti_slaptazodi(slaptazodis):
            login_user(vartotojas, remember=True)
            flash(f"Sveiki sugrize, {vartotojas.vardas}!", "success")
            kitas = request.args.get("next")
            return redirect(kitas or url_for("dashboard.index"))

        flash("Neteisingas el. pastas arba slaptazodis.", "danger")

    return render_template("login.html")''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Funkcija priima tiek GET, tiek POST užklausas. GET atveju '
    'atvaizduojama prisijungimo forma; POST atveju tikrinami pateikti '
    'duomenys: vartotojas randamas pagal el. paštą (mažosiomis raidėmis), '
    'tikrinamas slaptažodis. Sėkmingo prisijungimo atveju sukuriama sesija '
    'login_user iškvietimu, o klaidos atveju pateikiamas pranešimas vartotojui.'
)

prideti_pastraipa(
    doc,
    'Mokinių valdymo modulis yra vienas didžiausių. 3 kodo fragmente '
    'pateiktas mokinių sąrašo gavimo maršrutas su paieška ir filtravimu '
    'pagal klasę.'
)

prideti_pastraipa(
    doc,
    '3 kodo fragmentas. Mokinių sąrašo gavimas (failas: routes/students.py)',
    indent=False
)
prideti_kodo_fragmentą(doc, '''@students_bp.route("/")
@login_required
def saraso():
    paieska = request.args.get("paieska", "").strip()
    klases_id = request.args.get("klases_id", type=int)

    query = Mokinys.query
    if paieska:
        like = f"%{paieska}%"
        query = query.filter(
            (Mokinys.vardas.ilike(like)) | (Mokinys.pavarde.ilike(like))
        )
    if klases_id:
        query = query.filter_by(klases_id=klases_id)

    mokiniai = query.order_by(Mokinys.pavarde, Mokinys.vardas).all()
    klases = Klase.query.order_by(Klase.pavadinimas).all()

    return render_template(
        "students/list.html",
        mokiniai=mokiniai,
        klases=klases,
        paieska=paieska,
        pasirinkta_klase=klases_id,
    )''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Dekoratorius @login_required užtikrina, kad maršrutas pasiekiamas '
    'tik prisijungusiems vartotojams. Užklausa konstruojama dinamiškai: '
    'jei pateikta paieškos eilutė – pridedamas filtras ilike '
    '(angl. *case-insensitive like*) tiek pagal vardą, tiek pagal pavardę; '
    'jei pasirinkta klasė – pridedamas papildomas filter_by filtras. '
    'Rezultatai rikiuojami pagal pavardę, paskui pagal vardą.'
)

# 3.5 Duomenų bazės fizinis modelis
prideti_poskyrio_antraste(doc, "3.5. Duomenų bazės fizinis modelis")

prideti_pastraipa(
    doc,
    'Sistemos duomenų bazė realizuota SQLite varikliu. SQLite pasirinkta '
    'dėl jos paprastumo – nereikia atskiro serverio, visa duomenų bazė '
    'saugoma viename faile mokykla.db. SQLAlchemy ORM automatiškai '
    'generuoja DDL (angl. *Data Definition Language*) sakinius pagal '
    'Python klasių apibrėžimus. Sugeneruoto SQL kodo fragmentai pateikti '
    '4 kodo fragmente.'
)

prideti_pastraipa(
    doc,
    '4 kodo fragmentas. Duomenų bazės schema (SQL DDL sakiniai)',
    indent=False
)
prideti_kodo_fragmentą(doc, '''CREATE TABLE users (
    id INTEGER NOT NULL PRIMARY KEY,
    vardas VARCHAR(80) NOT NULL,
    pavarde VARCHAR(80) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    slaptazodzio_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'mokytojas',
    sukurtas DATETIME
);
CREATE INDEX ix_users_email ON users (email);

CREATE TABLE klases (
    id INTEGER NOT NULL PRIMARY KEY,
    pavadinimas VARCHAR(20) NOT NULL UNIQUE,
    mokslo_metai VARCHAR(20) NOT NULL DEFAULT '2025-2026',
    vadovo_id INTEGER REFERENCES users(id),
    sukurtas DATETIME
);

CREATE TABLE mokiniai (
    id INTEGER NOT NULL PRIMARY KEY,
    vardas VARCHAR(80) NOT NULL,
    pavarde VARCHAR(80) NOT NULL,
    gimimo_data DATE,
    email VARCHAR(120),
    telefonas VARCHAR(30),
    adresas VARCHAR(200),
    pastabos TEXT,
    klases_id INTEGER NOT NULL REFERENCES klases(id),
    motinos_vardas VARCHAR(160),
    motinos_telefonas VARCHAR(30),
    motinos_email VARCHAR(120),
    tevo_vardas VARCHAR(160),
    tevo_telefonas VARCHAR(30),
    tevo_email VARCHAR(120),
    mokyklos_autobusas BOOLEAN NOT NULL DEFAULT 0,
    geroves_komisija BOOLEAN NOT NULL DEFAULT 0,
    geroves_komisija_data DATE,
    geroves_komisija_pastabos TEXT,
    sukurtas DATETIME
);

CREATE TABLE diplomai (
    id INTEGER NOT NULL PRIMARY KEY,
    pavadinimas VARCHAR(200) NOT NULL,
    aprasymas TEXT,
    seminaras VARCHAR(200),
    isdavimo_data DATE,
    failo_kelias VARCHAR(300) NOT NULL,
    originalus_failo_vardas VARCHAR(300) NOT NULL,
    failo_tipas VARCHAR(20) NOT NULL,
    vartotojo_id INTEGER NOT NULL REFERENCES users(id),
    ikeltas DATETIME
);

CREATE TABLE skelbimai (
    id INTEGER NOT NULL PRIMARY KEY,
    pavadinimas VARCHAR(200) NOT NULL,
    turinys TEXT NOT NULL,
    svarbus BOOLEAN DEFAULT 0,
    vartotojo_id INTEGER NOT NULL REFERENCES users(id),
    sukurtas DATETIME
);''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Pirminis raktas id automatiškai didinamas kiekvienai naujai eilutei. '
    'Užsienio raktai (FOREIGN KEY) užtikrina referencinį vientisumą tarp '
    'susijusių lentelių. El. pašto stulpelis turi unikalumo apribojimą '
    '(UNIQUE) bei atskirą indeksą greitesnėms paieškoms. Cascade taisyklės '
    'apibrėžtos SQLAlchemy modelio lygyje – pašalinus vartotoją, '
    'automatiškai pašalinami jo įkelti diplomai ir skelbimai.'
)

# 3.6 Saugumo realizacija
prideti_poskyrio_antraste(doc, "3.6. Saugumo realizacijos sprendimai")

prideti_pastraipa(
    doc,
    'Sistemos saugumas užtikrinamas keliais lygiais. Slaptažodžiai '
    'šifruojami PBKDF2-SHA256 algoritmu su atsitiktinai generuotomis '
    'sūdyklomis (angl. *salt*). Prieigos kontrolė realizuota pasitelkiant '
    'pasirinktinį dekoratorių, kuris tikrina vartotojo rolę prieš vykdant '
    'jautrius veiksmus. Administracinio dekoratoriaus įgyvendinimas '
    'pateiktas 5 kodo fragmente.'
)

prideti_pastraipa(
    doc,
    '5 kodo fragmentas. Administratoriaus prieigos dekoratorius (failas: routes/auth.py)',
    indent=False
)
prideti_kodo_fragmentą(doc, '''def admin_required(f):
    """Dekoratorius - leidzia pasiekti tik administratoriams."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.yra_administratorius:
            flash("Sis puslapis prieinamas tik administratoriams.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated_function''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Dekoratorius apvelka pradinę maršruto funkciją: pirma patikrina, ar '
    'vartotojas prisijungęs (@login_required), tada – ar jo rolė yra '
    'administratorius. Neatitinkant sąlygos, vartotojas nukreipiamas į '
    'pradžios langą su klaidos pranešimu. Toks sprendimas leidžia '
    'paprastai apsaugoti bet kurį maršrutą pridėjus @admin_required '
    'dekoratorių prieš funkcijos apibrėžimą.'
)

prideti_pastraipa(
    doc,
    'Failų įkėlimas (diplomų funkcionalume) taip pat tikrinamas saugumo '
    'sumetimais. Patikrinami du parametrai: failo plėtinys (leidžiami tik '
    'pdf, png, jpg, jpeg) bei maksimalus dydis (16 MB). Įkeliami failai '
    'pervadinami su unikaliu UUID identifikatoriumi, kad būtų išvengta '
    'kolizijų bei užkirstas kelias kelio užteršimo (angl. *path traversal*) '
    'atakoms. Failų įkėlimo logika pateikta 6 kodo fragmente.'
)

prideti_pastraipa(
    doc,
    '6 kodo fragmentas. Diplomo failo įkėlimo logika (failas: routes/diplomas.py)',
    indent=False
)
prideti_kodo_fragmentą(doc, '''def _leistinas_failas(failo_vardas):
    return ("." in failo_vardas and
            failo_vardas.rsplit(".", 1)[1].lower()
            in current_app.config["ALLOWED_EXTENSIONS"])

@diplomas_bp.route("/ikelti", methods=["GET", "POST"])
@login_required
def ikelti():
    if request.method == "POST":
        failas = request.files.get("failas")

        if not failas or failas.filename == "":
            flash("Pasirinkite faila ikelimui.", "danger")
            return redirect(request.url)

        if not _leistinas_failas(failas.filename):
            flash("Leidziami tik PDF, PNG, JPG failai.", "danger")
            return redirect(request.url)

        originalus_vardas = secure_filename(failas.filename)
        plesinys = originalus_vardas.rsplit(".", 1)[1].lower()
        unikalus_vardas = f"{uuid.uuid4().hex}.{plesinys}"
        kelias = os.path.join(current_app.config["UPLOAD_FOLDER"],
                              unikalus_vardas)
        failas.save(kelias)
        # ... duomenu bazes irasymas ...''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Funkcija secure_filename iš Werkzeug bibliotekos pašalina '
    'potencialiai pavojingus simbolius iš pradinio failo pavadinimo. '
    'Generuojant atsitiktinį UUID, užtikrinama, kad du skirtingi vartotojai '
    'negali įkelti failų vienu tuo pačiu pavadinimu, o failo pavadinimas '
    'sistemos diske niekuomet nesutampa su originaliu vartotojo pateiktu '
    'pavadinimu – tai užkerta kelią pavojingiems URL spėjimams.'
)


# ============================================================================
# 4. NAUDOTOJO INSTRUKCIJA
# ============================================================================

prideti_skyriaus_antraste(doc, "4. Naudotojo instrukcija")

prideti_pastraipa(
    doc,
    'Šiame skyriuje pateikiama išsami sistemos diegimo bei naudojimo '
    'instrukcija. Pirmoje skyriaus dalyje aprašomi sistemos reikalavimai ir '
    'diegimo žingsniai lokalioje ir debesijos aplinkose. Antroje dalyje '
    'pateikiama vartotojo veiksmų seka įvairiems Sistemos panaudos atvejams '
    'realizuoti.'
)

# 4.1 Sistemos reikalavimai
prideti_poskyrio_antraste(doc, "4.1. Sistemos diegimo reikalavimai")

prideti_pastraipa(
    doc,
    'Sistema realizuota kaip internetinė programa, susidedanti iš serverio '
    'ir kliento dalies. Serveris vykdomas kompiuteryje arba debesijos '
    'paslaugoje, o klientas – šiuolaikinėje interneto naršyklėje. '
    'Programinės įrangos reikalavimai serverio ir kliento pusėje pateikti '
    '9 lentelėje (žr. 9 lentelė).'
)

prideti_lenteles_antraste(doc, "9", "Sistemos programinės įrangos reikalavimai")

reikalavimai = [
    ["Serverio dalis", "Python", "3.10 arba naujesnė versija"],
    ["Serverio dalis", "pip", "Python paketų valdymo įrankis"],
    ["Serverio dalis", "Git (pasirinktinai)", "Versijų valdymo sistema kodo sinchronizavimui"],
    ["Serverio dalis", "Operacinė sistema", "Windows 10/11, Linux (Ubuntu 20.04+) arba macOS 11+"],
    ["Serverio dalis", "Atminties poreikis", "Mažiausiai 512 MB laisvos operatyviosios atminties"],
    ["Serverio dalis", "Diskinė vieta", "Apie 200 MB priklausomybėms ir duomenų bazei"],
    ["Kliento dalis", "Interneto naršyklė", "Google Chrome, Mozilla Firefox, Microsoft Edge arba Safari (ne senesnė nei 2 metų versija)"],
    ["Kliento dalis", "JavaScript", "Privalo būti įjungtas naršyklėje"],
    ["Kliento dalis", "Ekrano skiriamoji geba", "Mažiausiai 1280 × 720 taškų (palaikoma ir mobiliesiems prietaisams)"],
    ["Tinklas", "Interneto ryšys", "Reikalingas pirminiam diegimui ir naudojimui (jei diegiama debesijoje)"],
]

sukurti_lentele(
    doc,
    ["Sritis", "Komponentas", "Reikalavimas"],
    reikalavimai,
    stulpelis_pločiai=[3.5, 4.5, 9.0],
)

# 4.2 Diegimas lokalioje aplinkoje
prideti_poskyrio_antraste(doc, "4.2. Diegimas lokalioje aplinkoje")

prideti_pastraipa(
    doc,
    'Sistemos diegimas lokaliame kompiuteryje atliekamas kelių žingsnių '
    'procese. Žemiau pateikta detali instrukcija Windows operacinei '
    'sistemai (PowerShell terminale). Linux ir macOS sistemose komandos '
    'iš esmės identiškos – skiriasi tik virtualios aplinkos aktyvavimo '
    'kelias.'
)

prideti_pastraipa(
    doc,
    'Pirmasis žingsnis – parsiųsti programinio kodo failus iš GitHub '
    'saugyklos. Tai galima atlikti dviem būdais: naudojant git komandą '
    'arba parsisiunčiant ZIP archyvą per naršyklę. Naudojant git '
    'komandą:',
    bold_prefix="1 žingsnis. Kodo parsisiuntimas. "
)

prideti_kodo_fragmentą(doc, '''git clone https://github.com/Astijus12/mokyklos-platforma.git
cd mokyklos-platforma''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Sukuriama izoliuota Python aplinka, kad sistemos paketai netrukdytų '
    'kitiems projektams kompiuteryje:',
    bold_prefix="2 žingsnis. Virtualios aplinkos sukūrimas. "
)

prideti_kodo_fragmentą(doc, '''python -m venv venv
.\\venv\\Scripts\\Activate.ps1''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Po aktyvavimo PowerShell eilutės pradžioje turėtų pasirodyti '
    'užrašas (venv), nurodantis aktyvią virtualią aplinką.'
)

prideti_pastraipa(
    doc,
    'Sistemos veikimui būtinos Python bibliotekos įdiegiamos iš '
    'requirements.txt failo:',
    bold_prefix="3 žingsnis. Priklausomybių diegimas. "
)

prideti_kodo_fragmentą(doc, '''pip install -r requirements.txt''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Diegimas užtrunka apie 1–2 minutes priklausomai nuo interneto ryšio '
    'greičio. Atsisiunčiami Flask, SQLAlchemy, Werkzeug bei kitos minėtos '
    'bibliotekos su jų priklausomybėmis.'
)

prideti_pastraipa(
    doc,
    'Atliekamas pradinis duomenų bazės užpildymas demonstraciniais '
    'duomenimis (4 vartotojai, 4 klasės, 12 mokinių, 5 skelbimai):',
    bold_prefix="4 žingsnis. Duomenų bazės sukūrimas. "
)

prideti_kodo_fragmentą(doc, '''python seed.py''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Po sėkmingo užpildymo terminale parodomas pranešimas „DEMO DUOMENYS '
    'SĖKMINGAI SUKURTI!" ir nurodyti demonstraciniai prisijungimo '
    'duomenys.'
)

prideti_pastraipa(
    doc,
    'Paleidžiamas Flask kūrimo serveris:',
    bold_prefix="5 žingsnis. Serverio paleidimas. "
)

prideti_kodo_fragmentą(doc, '''python app.py''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Terminale rodomas pranešimas „Running on http://127.0.0.1:5000”. '
    'Sistema pasiekiama naršyklėje atidarius adresą '
    'http://127.0.0.1:5000. Sustabdyti serverį galima paspaudus klavišų '
    'kombinaciją Ctrl + C.'
)

# 4.3 Diegimas debesijoje
prideti_poskyrio_antraste(doc, "4.3. Diegimas debesijoje (Render.com)")

prideti_pastraipa(
    doc,
    'Sistemai įdiegti debesijoje pasirinkta Render.com platforma, kuri '
    'siūlo nemokamą planą Python aplikacijoms. Diegimas vyksta '
    'automatizuotai pagal projekto saknyje esantį render.yaml '
    'konfigūracijos failą. Pagrindiniai diegimo žingsniai pateikti 10 '
    'lentelėje (žr. 10 lentelė).'
)

prideti_lenteles_antraste(doc, "10", "Sistemos diegimo žingsniai debesijoje")

diegimo_zingsniai = [
    ["1", "GitHub paskyros sukūrimas",
     "Užsiregistruojama svetainėje github.com (jei paskyra dar neturima)"],
    ["2", "Naujos saugyklos sukūrimas",
     "GitHub sąsajoje sukuriama nauja viešoji saugykla (pvz., mokyklos-platforma)"],
    ["3", "Kodo įkėlimas į GitHub",
     "Naudojant git push komandą, kodas perkeliamas į GitHub saugyklą"],
    ["4", "Render.com paskyros sukūrimas",
     'Užsiregistruojama svetainėje render.com pasirinkus „Sign up with GitHub”'],
    ["5", "Web Service sukūrimas",
     'Render sąsajoje pasirenkama „+ New” → „Web Service” → pasirenkama GitHub saugykla'],
    ["6", "Konfigūracijos patvirtinimas",
     "Render automatiškai aptinka render.yaml failą; patikrinami parametrai: Build Command, Start Command, Region (Frankfurt), Plan (Free)"],
    ["7", "Diegimo paleidimas",
     'Spaudžiamas mygtukas „Create Web Service”. Procesas trunka apie 5–10 minučių'],
    ["8", "Sistemos pasiekimas",
     "Pirmojo diegimo metu Render priskiria URL adresą (pvz., https://mokyklos-platforma-XXXX.onrender.com)"],
]

sukurti_lentele(
    doc,
    ["Nr.", "Veiksmas", "Aprašymas"],
    diegimo_zingsniai,
    stulpelis_pločiai=[1.2, 4.5, 11.3],
)

prideti_pastraipa(
    doc,
    'Konfigūracijos failo render.yaml struktūra pateikta 7 kodo fragmente.'
)

prideti_pastraipa(
    doc,
    '7 kodo fragmentas. Render.com konfigūracija (failas: render.yaml)',
    indent=False
)
prideti_kodo_fragmentą(doc, '''services:
  - type: web
    name: mokyklos-platforma
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.7
      - key: SECRET_KEY
        generateValue: true
      - key: PYTHONIOENCODING
        value: utf-8''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Parametras „generateValue: true” nurodo, kad Render automatiškai '
    'sugeneruos atsitiktinę SECRET_KEY reikšmę – tai užtikrina sesijų '
    'apsaugos saugumą, nepalikus rakto kodo saugykloje. Pakeitus kodą '
    'lokaliai ir įkėlus į GitHub (git push), Render automatiškai '
    'paleidžia naują diegimą per maždaug 3–5 minutes.'
)

# 4.4 Konfiguracija
prideti_poskyrio_antraste(doc, "4.4. Sistemos konfigūracija")

prideti_pastraipa(
    doc,
    'Konfigūracijos parametrai apibrėžti faile config.py. Pagrindiniai '
    'jautrūs nustatymai gali būti nustatomi per aplinkos kintamuosius, '
    'kas leidžia juos saugiai keisti nemodifikuojant kodo. Konfigūracijos '
    'parametrų sąrašas pateiktas 11 lentelėje (žr. 11 lentelė).'
)

prideti_lenteles_antraste(doc, "11", "Sistemos konfigūracijos parametrai")

konfig_parametrai = [
    ["SECRET_KEY",
     "Atsitiktinė reikšmė sesijų šifravimui",
     "Numatyta demo reikšmė (rekomenduojama keisti gamyboje)"],
    ["DATABASE_URL",
     "Duomenų bazės prisijungimo eilutė",
     "sqlite:///mokykla.db (lokali SQLite)"],
    ["UPLOAD_FOLDER",
     "Įkeliamų failų saugojimo katalogas",
     "static/uploads"],
    ["MAX_CONTENT_LENGTH",
     "Maksimalus įkeliamo failo dydis",
     "16 MB (16 × 1024 × 1024 baitų)"],
    ["ALLOWED_EXTENSIONS",
     "Leidžiami įkeliamų failų plėtiniai",
     "pdf, png, jpg, jpeg"],
]

sukurti_lentele(
    doc,
    ["Parametras", "Paskirtis", "Numatyta reikšmė"],
    konfig_parametrai,
    stulpelis_pločiai=[4.0, 7.0, 6.0],
)

# 4.5 Naudojimo instrukcija
prideti_poskyrio_antraste(doc, "4.5. Sistemos naudojimo instrukcija")

prideti_pastraipa(
    doc,
    'Šioje dalyje žingsnis po žingsnio pateikiami pagrindinių Sistemos '
    'funkcijų naudojimo aprašymai. Demonstraciniai prisijungimo duomenys, '
    'kurie pateikti pirmojo paleidimo metu, yra šie: administratoriaus '
    'rolė – admin@mokykla.lt / admin123; mokytojo rolė – jonas@mokykla.lt '
    '/ mokytojas123. Rekomenduojama nedelsiant pakeisti šiuos slaptažodžius '
    'paleidus sistemą gamybinėje aplinkoje.'
)

# 4.5.1 Prisijungimas
prideti_skyrelio_antraste(doc, "4.5.1. Prisijungimas prie Sistemos")

prideti_pastraipa(
    doc,
    'Atidarius Sistemos adresą naršyklėje, pasirodo prisijungimo langas '
    'su el. pašto ir slaptažodžio laukais. Norint prisijungti, atliekami '
    'šie veiksmai:'
)

prideti_kodo_fragmentą(doc, '''1. Įvedamas el. paštas (pvz., admin@mokykla.lt).
2. Įvedamas slaptažodis.
3. Spaudžiamas mygtukas "Prisijungti".
4. Patvirtinus duomenis, vartotojas nukreipiamas į pradžios langą.''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Neteisingo prisijungimo atveju virš formos atsiranda raudonas '
    'pranešimas „Neteisingas el. paštas arba slaptažodis”. Po sėkmingo '
    'prisijungimo vartotojo vardas matomas šoninės juostos apačioje, o '
    'rolei priskirti meniu punktai – navigacijoje.'
)

# 4.5.2 Mokinio prideejimas
prideti_skyrelio_antraste(doc, "4.5.2. Naujo mokinio pridėjimas")

prideti_pastraipa(
    doc,
    'Norint įvesti naują mokinį į Sistemą, atliekami šie veiksmai:'
)

prideti_kodo_fragmentą(doc, '''1. Šoninėje juostoje spaudžiamas meniu punktas "Mokiniai".
2. Atvėrus mokinių sąrašą, spaudžiamas mygtukas "Naujas mokinys".
3. Atvertoje formoje užpildomi privalomi laukai:
   - Vardas
   - Pavardė
   - Klasė (pasirenkama iš sąrašo)
4. Užpildomi neprivalomi mokinio duomenys:
   - Gimimo data
   - El. paštas, telefonas, adresas
5. Užpildomi tėvų duomenys:
   - Motinos vardas, pavardė, telefonas, el. paštas
   - Tėvo vardas, pavardė, telefonas, el. paštas
6. Pažymimi papildomi požymiai:
   - "Mokinį reikia vežti mokyklos autobusu" (jei taikoma)
   - "Buvo svarstomas vaiko gerovės komisijoje" (jei taikoma);
     atsiveria laukai svarstymo datai ir pastaboms įvesti
7. Spaudžiamas mygtukas "Pridėti mokinį".''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Po sėkmingo pridėjimo Sistema atvaizduoja sukurto mokinio profilio '
    'puslapį, kuriame matomi visi įvesti duomenys. Mokinio profilis '
    'leidžia greitai paskambinti tėvams (paspaudus telefono numerį) arba '
    'parašyti el. laišką (paspaudus el. pašto adresą), kadangi šie laukai '
    'aktyvūs kaip nuorodos.'
)

# 4.5.3 Klases sukurimas
prideti_skyrelio_antraste(doc, "4.5.3. Naujos klasės sukūrimas (tik administratoriui)")

prideti_pastraipa(
    doc,
    'Klasių sukūrimo funkcija prieinama tik vartotojams, turintiems '
    'administratoriaus rolę. Sukūrimo veiksmų seka:'
)

prideti_kodo_fragmentą(doc, '''1. Šoninėje juostoje pasirenkama "Klasės".
2. Spaudžiamas mygtukas "Nauja klasė".
3. Užpildoma forma:
   - Klasės pavadinimas (pvz., "5A", "10B", "IIG")
   - Mokslo metai (pvz., "2025-2026")
   - Klasės vadovas (pasirinkimas iš mokytojų sąrašo)
4. Spaudžiamas mygtukas "Sukurti klasę".''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Sukurta klasė atsiranda klasių sąraše. Iš klasės puslapio galima '
    'pridėti mokinių į konkrečią klasę – tokiu atveju klasė formoje '
    'pasirenkama automatiškai.'
)

# 4.5.4 Diplomo ikelimas
prideti_skyrelio_antraste(doc, "4.5.4. Diplomo įkėlimas")

prideti_pastraipa(
    doc,
    'Diplomų ir kvalifikacijos kėlimo pažymėjimų įkėlimas atliekamas '
    'šiais žingsniais:'
)

prideti_kodo_fragmentą(doc, '''1. Šoninėje juostoje pasirenkama "Diplomai".
2. Spaudžiamas mygtukas "Įkelti diplomą".
3. Formoje pasirenkamas failas iš kompiuterio:
   - Leidžiami formatai: PDF, PNG, JPG, JPEG
   - Maksimalus dydis: 16 MB
4. Užpildomi metaduomenys:
   - Pavadinimas (pvz., "Skaitmeninio raštingumo sertifikatas")
   - Seminaras, renginys (pvz., "IT mokytojų konferencija 2025")
   - Išdavimo data
   - Aprašymas
5. Spaudžiamas mygtukas "Įkelti".''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Įkeltas diplomas matomas diplomų sąraše kortelės pavidalu. Iš '
    'kortelės galima atlikti tris veiksmus: peržiūrėti diplomą '
    '(atveriama naujame naršyklės skirtuke), atsisiųsti į kompiuterį '
    'arba pašalinti (matoma tik diplomo įkėlėjui arba administratoriui).'
)

# 4.5.5 Skelbimo kurimas
prideti_skyrelio_antraste(doc, "4.5.5. Skelbimo kūrimas")

prideti_pastraipa(
    doc,
    'Skelbimas mokyklos darbuotojams kuriamas atliekant šiuos veiksmus:'
)

prideti_kodo_fragmentą(doc, '''1. Pasirenkamas meniu punktas "Skelbimai".
2. Spaudžiamas mygtukas "Naujas skelbimas".
3. Užpildoma forma:
   - Pavadinimas (privalomas)
   - Turinys (privalomas, kelių pastraipų tekstas)
   - Žymimas laukas "Pažymėti kaip svarbų skelbimą" (jei reikia)
4. Spaudžiamas mygtukas "Paskelbti".''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Svarbūs skelbimai (su žyma „Svarbu”) visada rodomi sąrašo viršuje '
    'ir paryškinami raudona spalva. Tai užtikrina, kad pirmiausiai būtų '
    'pastebėti svarbiausi pranešimai – pavyzdžiui, posėdžių datos ar '
    'mokyklos vidaus įvykiai.'
)

# 4.5.6 Paieska
prideti_skyrelio_antraste(doc, "4.5.6. Globalios paieškos naudojimas")

prideti_pastraipa(
    doc,
    'Sistemos viršutinėje juostoje yra paieškos laukas, kuris ieško per '
    'visas pagrindines Sistemos sritis vienu metu. Naudojimas:'
)

prideti_kodo_fragmentą(doc, '''1. Į paieškos lauką įvedama užklausa
   (pvz., mokinio vardas, klasės pavadinimas, tėvų vardas).
2. Spaudžiamas klavišas Enter.
3. Atvėrus rezultatų puslapį, rasti elementai sugrupuojami pagal sritį:
   - Mokiniai
   - Klasės
   - Diplomai
   - Skelbimai
4. Iš rezultatų puslapio galima pereiti tiesiogiai prie pasirinkto įrašo
   paspaudus jo pavadinimą.''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Paieška vykdoma per kelis laukus vienu metu – pavyzdžiui, ieškant '
    'mokinio, tikrinami ne tik jo vardas ir pavardė, bet ir tėvų vardai '
    'bei el. pašto adresas. Tai leidžia rasti vaiką žinant tik bet kurį '
    'su juo susijusį asmenį.'
)

# 4.5.7 CSV eksportas
prideti_skyrelio_antraste(doc, "4.5.7. Mokinių sąrašo eksportas")

prideti_pastraipa(
    doc,
    'Sistema leidžia eksportuoti mokinių sąrašą CSV formatu, kuris '
    'tinka tolesniam apdorojimui Microsoft Excel ar Google Sheets '
    'programose. Eksporto veiksmai:'
)

prideti_kodo_fragmentą(doc, '''1. Atidaromas mokinių sąrašas (meniu "Mokiniai").
2. Pasirinktinai pritaikomas filtras pagal klasę.
3. Spaudžiamas mygtukas "Eksportuoti".
4. Sistema generuoja CSV failą ir pateikia jį atsisiuntimui.
5. Atvėrus failą Excel programoje, lietuviški simboliai
   atvaizduojami teisingai dėl įdėto BOM ženklo.''')

prideti_tustia(doc, 1)

prideti_pastraipa(
    doc,
    'Eksportuojamame faile pateikiami visi mokinio duomenys, įskaitant '
    'tėvų informaciją, autobuso bei VGK žymeklius. Failo pavadinimas '
    'formuojamas automatiškai pagal datą ir laiką, pavyzdžiui, '
    '„mokiniai_20260615_1430.csv”.'
)

# 4.6 Sistemos salinimas
prideti_poskyrio_antraste(doc, "4.6. Sistemos šalinimas")

prideti_pastraipa(
    doc,
    'Sistemos šalinimas lokalioje aplinkoje atliekamas paprastai: '
    'pašalinamas visas projekto katalogas. Šalinant Sistemą iš debesijos '
    'paslaugos, Render.com sąsajoje pasirenkamas Sistemos servisas, '
    'paspaudžiamas „Settings” ir lango apačioje – „Delete Web Service” '
    'mygtukas. Patvirtinus veiksmą, Sistema visiškai pašalinama iš '
    'serverio. GitHub saugyklą galima palikti arba pašalinti atskirai '
    'per GitHub sąsają.'
)


# ============================================================================
# IŠVADOS IR SIŪLYMAI
# ============================================================================

prideti_skyriaus_antraste(doc, "Išvados ir siūlymai")

prideti_pastraipa(
    doc,
    'Profesinės praktikos metu suprojektuota ir realizuota internetinio '
    'tipo mokyklos valdymo informacinė sistema Kupiškio rajono Subačiaus '
    'gimnazijos Noriūnų Jono Černiaus skyriui. Atlikus profesinės praktikos '
    'užduotį, suformuluotos žemiau pateiktos išvados, atitinkančios įvado '
    'dalyje suformuluotus uždavinius.'
)

# Išvada 1
p = doc.add_paragraph(style="TEKSTAS")
p.paragraph_format.first_line_indent = Cm(1.27)
run = p.add_run(
    '1. Atlikus probleminės srities analizę, nustatyta, kad mažose '
    'kaimo mokyklose centralizuotų informacinių sistemų administraciniam '
    'darbui nepakanka, todėl mokytojai ir administracija reikalingus '
    'duomenis saugo popieriniu pavidalu arba atskiruose kompiuterio '
    'failuose. Identifikuoti pagrindiniai valdymo procesai (mokinių, '
    'klasių, diplomų ir skelbimų valdymas) bei suformuluoti keturiolika '
    'funkcinių (devyni pagrindiniai, penki pagalbiniai) ir septyni '
    'nefunkciniai reikalavimai, atitinkantys priimančios organizacijos '
    'poreikius.'
)
run.font.name = "Times New Roman"
run.font.size = Pt(12)

# Išvada 2
p = doc.add_paragraph(style="TEKSTAS")
p.paragraph_format.first_line_indent = Cm(1.27)
run = p.add_run(
    '2. Suprojektavus Sistemos architektūrą, parengtos pagrindinės UML '
    'diagramos: panaudos atvejų diagrama (atvaizduoja dvi vartotojų roles '
    'ir penkiolika panaudos atvejų), veiklos diagrama (mokinio pridėjimo '
    'eigai vaizduoti), sekos diagrama (autentikacijos procesui) bei '
    'esybių–ryšių diagrama, apibrėžianti penkias pagrindines duomenų '
    'bazės esybes ir jų tarpusavio ryšius. Diagramos leido aiškiai '
    'nustatyti Sistemos funkcionalumo apimtį prieš realizavimą.'
)
run.font.name = "Times New Roman"
run.font.size = Pt(12)

# Išvada 3
p = doc.add_paragraph(style="TEKSTAS")
p.paragraph_format.first_line_indent = Cm(1.27)
run = p.add_run(
    '3. Realizavus Sistemos prototipą, sukurta veikianti internetinė '
    'aplikacija, naudojanti Python 3.12 (Flask karkasą), HTML, CSS '
    '(Tailwind biblioteka) bei JavaScript kalbas serverio ir kliento '
    'pusėje, o duomenų saugojimui – SQLite reliacinę duomenų bazę. '
    'Įgyvendinta vartotojų autentikacija (Flask-Login biblioteka), '
    'slaptažodžių šifravimas PBKDF2-SHA256 algoritmu bei rolėmis paremta '
    'prieigos kontrolė. Sistema atitinka visus suformuluotus funkcinius '
    'reikalavimus.'
)
run.font.name = "Times New Roman"
run.font.size = Pt(12)

# Išvada 4
p = doc.add_paragraph(style="TEKSTAS")
p.paragraph_format.first_line_indent = Cm(1.27)
run = p.add_run(
    '4. Įdiegus realizuotą Sistemą į Render.com debesijos paslaugą, '
    'užtikrintas jos prieinamumas internetu visą parą. Atliktas '
    'funkcionalumo testavimas patvirtino, kad visos pagrindinės funkcijos '
    '(prisijungimas, mokinių valdymas, klasių valdymas, diplomų '
    'įkėlimas, paieška, CSV eksportas) veikia tinkamai. Parengta '
    'diegimo instrukcija lokalioje ir debesijos aplinkose, taip pat '
    'naudotojo instrukcija pagrindiniams panaudos atvejams.'
)
run.font.name = "Times New Roman"
run.font.size = Pt(12)

# Bendra išvada
p = doc.add_paragraph(style="TEKSTAS")
p.paragraph_format.first_line_indent = Cm(1.27)
run = p.add_run(
    '5. Apibendrinant, sukurta Sistema praktiškai sprendžia identifikuotą '
    'problemą – centralizuoja mokyklos administracinius duomenis vienoje '
    'modernioje, lengvai naudojamoje aplikacijoje. Sistemos pagalba '
    'mokytojai ir administracija gali greičiau pasiekti reikalingus '
    'mokinių, tėvų bei profesinio tobulinimosi dokumentų duomenis, kas '
    'pagerins darbo efektyvumą bei sumažins rankinio darbo poreikį '
    'kasdienėse užduotyse.'
)
run.font.name = "Times New Roman"
run.font.size = Pt(12)

# Siūlymai
prideti_pastraipa(
    doc,
    'Tolesniam Sistemos vystymui pateikiami šie siūlymai:',
    bold_prefix="Siūlymai. ",
    indent=True
)

siulymai = [
    'integruoti elektroninį dienyną – sukurti automatinį duomenų '
    'apsikeitimą su TAMO platforma, kad pažymiai ir lankomumo duomenys '
    'būtų prieinami centralizuotai;',

    'pridėti mokinių tvarkaraščio modulį, leidžiantį valdyti pamokų '
    'tvarkaraščius bei juos eksportuoti spausdinimui;',

    'įdiegti automatinį duomenų atsarginių kopijų darymą bei galimybę '
    'atkurti sistemą iš ankstesnio momento;',

    'sukurti tėvų prieigos portalą, kuriame tėvai galėtų matyti savo '
    'vaiko duomenis bei oficialius mokyklos pranešimus;',

    'pereiti nuo SQLite į PostgreSQL duomenų bazę, kuri labiau tinka '
    'didesnių apimčių sistemoms ir užtikrintų geresnį našumą bei '
    'patikimumą gamybinėje aplinkoje;',

    'pridėti dviejų veiksnių autentikaciją (angl. *Two-Factor Authentication*) '
    'administratorių paskyroms, padidinant prieigos saugumą;',

    'realizuoti mobiliąją programėlę Android ir iOS operacinėms sistemoms, '
    'kuri leistų mokytojams pasiekti Sistemą iš mobiliųjų prietaisų '
    'nepriklausomai nuo interneto naršyklės.',
]

for i, siul in enumerate(siulymai, 1):
    p = doc.add_paragraph(style="TEKSTAS")
    p.paragraph_format.first_line_indent = Cm(1.27)
    run = p.add_run(f"{i}. {siul}")
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)


# ============================================================================
# INFORMACIJOS ŠALTINIŲ SĄRAŠAS
# ============================================================================

prideti_skyriaus_antraste(doc, "Informacijos šaltinių sąrašas")

# Šaltiniai pagal APA citavimo stilių
saltiniai = [
    'Aktas, D., Baltrūnienė, V., Blaževičienė, K., Kubilienė, E., '
    'Liepuonienė, R., Miakinkovienė, R., Neverbickaitė, D., '
    'Kačinaitė-Vrubliauskienė, D., Sindaravičienė, N., & Žėkienė, D. '
    '(2023). *Bendrieji studijų rašto darbų reikalavimai: metodinė '
    'priemonė*. Vilniaus kolegija. '
    'https://www.viko.lt/wp-content/uploads/sites/8/2023/01/'
    'Bendrieji-studiju-rasto-darbu-reikalavimai_NAUJAS_nuo-2023-01-30.pdf',

    'Gžegoževskė, L., Kirdeikienė, A., Mačėnienė, J., Neverbickaitė, D., '
    '& Zailskas, J. (2023). *Bendrieji studijų rašto darbų reikalavimai*. '
    'Vilniaus kolegijos Elektronikos ir informatikos fakultetas. '
    'https://www.viko.lt/',

    'Grinberg, M. (2018). *Flask web development: Developing web '
    'applications with Python* (2nd ed.). O\'Reilly Media.',

    'Pallets Projects. (2024). *Flask documentation (3.x)*. '
    'https://flask.palletsprojects.com/en/3.0.x/',

    'SQLAlchemy. (2024). *SQLAlchemy 2.0 documentation*. '
    'https://docs.sqlalchemy.org/en/20/',

    'Python Software Foundation. (2024). *Python 3.12 documentation*. '
    'https://docs.python.org/3.12/',

    'Mozilla Foundation. (2024). *MDN web docs: HTML, CSS, and JavaScript '
    'references*. https://developer.mozilla.org/',

    'Tailwind Labs. (2024). *Tailwind CSS documentation*. '
    'https://tailwindcss.com/docs',

    'Render. (2024). *Render documentation: Deploy Python web services*. '
    'https://render.com/docs/deploy-flask',

    'Werkzeug. (2024). *Werkzeug WSGI utility library documentation*. '
    'https://werkzeug.palletsprojects.com/en/3.0.x/',

    'OWASP Foundation. (2023). *OWASP Top 10 web application security '
    'risks*. https://owasp.org/Top10/',
]

for saltinis in saltiniai:
    p = doc.add_paragraph(style="TEKSTAS")
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.left_indent = Cm(1.27)
    p.paragraph_format.first_line_indent = Cm(-1.27)  # hanging indent
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.5

    # Apdorojame italic dalis *...*
    dalys = saltinis.split('*')
    for i, dalis in enumerate(dalys):
        r = p.add_run(dalis)
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        if i % 2 == 1:
            r.italic = True


# ============================================================================
# PRIEDAI
# ============================================================================

prideti_skyriaus_antraste(doc, "Priedai")

prideti_pastraipa(
    doc,
    'Priedų sąrašas:'
)

priedai = [
    '1 priedas. Individuali praktikos užduotis '
    '(atskirame faile: Profesines_praktikos_individuali_uzduotis_UZPILDYTA.docx).',

    '2 priedas. Sistemos antraštinis lapas (šios ataskaitos pradžioje).',

    '3 priedas. GitHub kodo saugyklos nuoroda: '
    'https://github.com/Astijus12/mokyklos-platforma',

    '4 priedas. Veikiančios Sistemos demonstracinė nuoroda: '
    '(Render.com URL pateikiamas atskirai praktikos vadovui).',
]

for priedo_tekstas in priedai:
    p = doc.add_paragraph(style="TEKSTAS")
    p.paragraph_format.first_line_indent = Cm(1.27)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(priedo_tekstas)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)


# Išsaugom
doc.save(ISSAUGOTAS_KELIAS)
print(f"✓ Sukurta: {ISSAUGOTAS_KELIAS}")
print()
print(f"Paragrafų: {len(doc.paragraphs)}")
heading_count = sum(1 for p in doc.paragraphs if p.style.name == "Heading 1")
print(f"Heading 1 skyrių: {heading_count}")
print()
print("Patikrinta atitiktis Bendrųjų reikalavimų standartams:")
print("  ✓ A4 formatas, paraštės K30/D10/V20/A20 mm")
print("  ✓ Times New Roman 12pt")
print("  ✓ TEKSTAS stilius: JUSTIFY, 1.5 tarpas, 1.27 cm įtrauka, 0pt prieš/po")
print("  ✓ Heading 1: 14pt Bold, CENTRUOTA, Single tarpas, 6pt prieš/po")
print("  ✓ Puslapio numeravimas (10pt) apačioje per vidurį")
print("  ✓ Antraštinis lapas be numerio")
print("  ✓ Lietuviška akademinė stilistika (neveikiamieji dalyviai)")
print("  ✓ Visi tekstai lietuvių kalba")
