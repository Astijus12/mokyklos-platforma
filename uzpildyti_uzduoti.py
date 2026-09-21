"""Užpildo Individualios praktikos užduoties (Priedas 2) .docx failą."""
import sys
from copy import deepcopy
from docx import Document
from docx.shared import Pt

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ORIGINAL = r"C:\Users\astij\OneDrive\Desktop\Profesines_praktikos_individuali_uzduotis.docx"
NAUJAS = r"C:\Users\astij\OneDrive\Desktop\Profesines_praktikos_individuali_uzduotis_UZPILDYTA.docx"


def pakeisti_paragrafa(p, naujas_tekstas, bold=False):
    """Pakeičia paragrafo tekstą išsaugodamas formatavimą."""
    # Pirma run'a paliekam, kitas išvalom
    if p.runs:
        first = p.runs[0]
        first.text = naujas_tekstas
        if bold:
            first.bold = True
        # Pašalinam likusias run'as
        for r in p.runs[1:]:
            r.text = ""
    else:
        run = p.add_run(naujas_tekstas)
        if bold:
            run.bold = True


def prideti_run(p, tekstas, bold=False, underline=False):
    """Prideda naują run prie paragrafo."""
    run = p.add_run(tekstas)
    if bold:
        run.bold = True
    if underline:
        run.underline = True
    return run


doc = Document(ORIGINAL)

# Paragraph 8: "Studentas(ė) ... Grupė ..."
p8 = doc.paragraphs[8]
# Išvalom esamą turinį ir užpildom
for r in p8.runs:
    r.text = ""
prideti_run(p8, "Studentas(ė) ", bold=False)
prideti_run(p8, "Astijus Grinevičius", bold=True)
prideti_run(p8, "\t\t\t\tGrupė ", bold=False)
prideti_run(p8, "PI23SN", bold=True)

# Paragraph 10: pabraukti "profesinė"
p10 = doc.paragraphs[10]
for r in p10.runs:
    r.text = ""
prideti_run(p10, "Praktikos pavadinimas: ", bold=False)
prideti_run(p10, "profesinė", bold=True, underline=True)
prideti_run(p10, " / baigiamoji.", bold=False)
prideti_run(p10, "(tinkamą pabraukti)", bold=False)

# Paragraph 11: Tikslas
p11 = doc.paragraphs[11]
for r in p11.runs:
    r.text = ""
prideti_run(p11, "Tikslas: ", bold=False)
prideti_run(
    p11,
    "Suprojektuoti ir realizuoti internetinę mokyklos valdymo sistemą "
    "Kupiškio r. Subačiaus gimnazijai (Noriūnų Jono Černiaus skyriui), skirtą "
    "mokytojams ir administracijai valdyti mokinių, klasių, tėvų bei profesinio "
    "tobulinimosi dokumentų duomenis.",
    bold=False
)

# Uždaviniai (paragrafai 13-16)
uzdaviniai = [
    "Atlikti probleminės srities analizę: identifikuoti mokyklos valdymo procesus, "
    "esamą informacinę aplinką ir suformuluoti kuriamos sistemos funkcinius bei "
    "nefunkcinius reikalavimus.",

    "Suprojektuoti sistemos architektūrą: parengti panaudos atvejų, veiklos, "
    "klasių bei esybių–ryšių diagramas, suplanuoti vartotojo sąsajos struktūrą.",

    "Realizuoti sistemą naudojant Python (Flask karkasą), HTML, CSS, JavaScript "
    "kalbas bei SQLite duomenų bazę; įgyvendinti vartotojų autentikaciją, "
    "rolėmis paremtą prieigą bei pagrindines duomenų valdymo funkcijas.",

    "Įdiegti realizuotą sistemą į debesijos serverį (Render.com), atlikti "
    "veikimo testavimą bei parengti diegimo ir naudotojo instrukcijas.",
]

# Užpildom 4 uždavinius (paragrafai 13-16)
for i, uzdavinio_tekstas in enumerate(uzdaviniai):
    p = doc.paragraphs[13 + i]
    for r in p.runs:
        r.text = ""
    prideti_run(p, uzdavinio_tekstas, bold=False)

# Paragraph 20: Priimančios organizacijos praktikos vadovas
p20 = doc.paragraphs[20]
for r in p20.runs:
    r.text = ""
prideti_run(p20, "Priimančios organizacijos praktikos vadovas ", bold=False)
prideti_run(p20, "Rita Grinevičienė, direktoriaus pavaduotoja ugdymui", bold=True)

# Paragraph 22: EIF praktikos vadovas
p22 = doc.paragraphs[22]
for r in p22.runs:
    r.text = ""
prideti_run(p22, "EIF praktikos vadovas ", bold=False)
prideti_run(p22, "doc. dr. R. Tumasonis, lektorius", bold=True)

# Paragraph 24: data
p24 = doc.paragraphs[24]
for r in p24.runs:
    r.text = ""
prideti_run(p24, "2026 m. balandžio 27 d.", bold=False)

doc.save(NAUJAS)
print(f"✓ Failas išsaugotas: {NAUJAS}")
print("\nPagrindiniai duomenys:")
print("  Studentas: Astijus Grinevičius")
print("  Grupė: PI23SN")
print("  Praktikos tipas: profesinė")
print("  Praktikos vieta: Kupiškio r. Subačiaus gimnazija (Noriūnų J. Černiaus skyrius)")
print("  Praktikos vadovas mokykloje: Rita Grinevičienė")
print("  EIF praktikos vadovas: doc. dr. R. Tumasonis")
print("  Data: 2026-04-27")
