"""Užpildo Praktikos vadovo vertinimo lapą.

Vertinimas atliktas iš mokyklos vadovo (Rita Grinevičienė) perspektyvos.
"""
import sys
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\vertinimo_sablonas.docx"
UZPILDYTAS = r"C:\Users\astij\OneDrive\Desktop\PI23SN_profesines_vertinimas_UZPILDYTAS.docx"


def istraukt_run_text_ir_papildyti(p, papildymas):
    """Papildo paragrafo paskutinį run'ą tekstu."""
    if p.runs:
        # Pridėkim naują run'ą su pildymu
        run = p.add_run(papildymas)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        return run


def pakeisti_pastraipa(p, naujas_tekstas, bold=False):
    """Pakeičia visą paragrafo turinį."""
    # Pašalinam visus run'us
    for r in p.runs:
        r.text = ""

    if p.runs:
        # Naudokim pirmą run'ą
        p.runs[0].text = naujas_tekstas
        p.runs[0].font.name = "Times New Roman"
        p.runs[0].font.size = Pt(12)
        if bold:
            p.runs[0].font.bold = True
    else:
        run = p.add_run(naujas_tekstas)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        if bold:
            run.font.bold = True


doc = Document(ORIGINAL)

# =============================================================================
# UZPILDYTI LAUKUS
# =============================================================================

# [4] Studentas(ė)______________ (vardas, pavardė)
pakeisti_pastraipa(
    doc.paragraphs[4],
    "Studentas(ė)\tAstijus Grinevičius"
)

# [10] Praktikos atlikimo vieta ______________
pakeisti_pastraipa(
    doc.paragraphs[10],
    "Praktikos atlikimo vieta\tKupiškio r. Subačiaus gimnazija"
)

# [11] -----------
pakeisti_pastraipa(
    doc.paragraphs[11],
    "\t\t\t(Noriūnų Jono Černiaus skyrius), Melioratorių g. 5, Noriūnai k., Kupiškio r."
)

# =============================================================================
# VERTINIMO DALYS
# =============================================================================

# 1. Požiūris į darbą
pakeisti_pastraipa(
    doc.paragraphs[21],
    "1. Požiūris į darbą (domėjimasis darbu, iniciatyvumas, pareigingumas, "
    "tvarkingumas, drausmė ir kt.): Studento požiūris į praktiką buvo pavyzdinis. "
    "Astijus aktyviai domėjosi mokyklos administraciniais procesais, savarankiškai "
    "iniciavo susitikimus su pedagoginiu personalu reikalavimams aiškintis. "
    "Pasižymėjo dideliu pareigingumu, atvyko laiku, visas užduotis atliko "
    "kruopščiai ir terminuotai. Bendraudamas su mokyklos darbuotojais buvo "
    "mandagus, dėmesingas ir profesionalus. Demonstravo aukštą motyvaciją bei "
    "stiprų norą sukurti realiai naudingą produktą mokyklos bendruomenei."
)

# 2. Teorinio parengimo trūkumai
pakeisti_pastraipa(
    doc.paragraphs[23],
    "2. Teorinio parengimo trūkumai, išryškėję praktikos metu: Esminių teorinio "
    "parengimo trūkumų praktikos metu nepastebėta. Studento technologinės žinios "
    "(Python, Flask, SQLite, HTML, CSS, JavaScript) atitiko keliamus reikalavimus. "
)

pakeisti_pastraipa(
    doc.paragraphs[24],
    "Nedidelių sunkumų buvo susijusių su projekto įdiegimu į debesijos paslaugą "
    "(Render.com), tačiau studentas savarankiškai išsiaiškino diegimo niuansus "
)

pakeisti_pastraipa(
    doc.paragraphs[25],
    "ir sėkmingai pristatė veikiantį produktą. Rekomenduotina ateityje gilinti "
)

pakeisti_pastraipa(
    doc.paragraphs[26],
    "žinias apie produkcinių sistemų diegimą bei duomenų bazių migracijų valdymą."
)

# Tuscios eilutes 27, 28
pakeisti_pastraipa(doc.paragraphs[27], "")
pakeisti_pastraipa(doc.paragraphs[28], "")

# 3. Atliktų užduočių kokybė
pakeisti_pastraipa(
    doc.paragraphs[30],
    "3. Atliktų užduočių kokybė, savarankiškumas: Praktikos metu studentas "
    "savarankiškai suprojektavo ir realizavo internetinę mokyklos valdymo "
    "informacinę sistemą, skirtą Subačiaus gimnazijos Noriūnų Jono Černiaus "
)

pakeisti_pastraipa(
    doc.paragraphs[31],
    "skyriaus mokytojams ir administracijai. Sistemoje įgyvendintos visos "
    "sutartos funkcijos: vartotojų autentikacija su rolėmis paremta prieiga, "
    "mokinių, klasių, tėvų duomenų valdymas, vaiko gerovės komisijos "
    "informacijos saugojimas, "
)

pakeisti_pastraipa(
    doc.paragraphs[32],
    "diplomų bei kvalifikacijos kėlimo dokumentų įkėlimas, vidiniai skelbimai, "
    "globali paieška bei CSV eksportas. Sistema sėkmingai įdiegta į debesijos "
    "platformą Render.com ir yra pasiekiama internetu. Visi darbai atlikti "
    "savarankiškai, kokybiškai, laikantis šiuolaikinių programinės įrangos "
    "kūrimo gerosios praktikos principų."
)

# 4. Praktinio darbo įvertinimas balais
pakeisti_pastraipa(
    doc.paragraphs[35],
    "4. Praktinio darbo įvertinimas balais\t10 (puikiai)"
)

# Priimančios organizacijos praktikos vadovas
pakeisti_pastraipa(
    doc.paragraphs[38],
    "Priimančios organizacijos praktikos vadovas\tRita Grinevičienė"
)

pakeisti_pastraipa(
    doc.paragraphs[39],
    "\t\t\t\t(direktoriaus pavaduotoja ugdymui)"
)

# Data
pakeisti_pastraipa(
    doc.paragraphs[44],
    "2026 m.\tbirželio\tmėn.\t19\td."
)

doc.save(UZPILDYTAS)
print(f"✓ Užpildytas vertinimo lapas išsaugotas:")
print(f"  {UZPILDYTAS}")
print()
print("UŽPILDYTA INFORMACIJA:")
print("  Studentas:        Astijus Grinevičius")
print("  Studijų programa: Programų sistemos")
print("  Grupė:            PI23SN")
print("  Praktikos vieta:  Kupiškio r. Subačiaus gimnazija")
print("                    (Noriūnų Jono Černiaus skyrius)")
print("  Trukmė:           2026-04-27 iki 2026-06-19 (12 kreditų)")
print("  EIF vadovas:      doc. dr. Romanas Tumasonis")
print("  Įmonės vadovas:   Rita Grinevičienė")
print("  Įvertinimas:      10 (puikiai)")
print("  Data:             2026 m. birželio 19 d.")
