"""Sutrumpina baigiamosios praktikos uždavinius."""
import sys
from docx import Document
from docx.shared import Pt

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\baigiamosios_uzduotis.docx"
NAUJAS = r"C:\Users\astij\OneDrive\Desktop\PI23SN_Baigiamosios_praktikos_v2.docx"


def prideti_run(p, tekstas, bold=False, underline=False):
    run = p.add_run(tekstas)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    if bold:
        run.bold = True
    if underline:
        run.underline = True
    return run


doc = Document(ORIGINAL)

# [8] Studentas + Grupė
p8 = doc.paragraphs[8]
for r in p8.runs:
    r.text = ""
prideti_run(p8, "Studentas(ė) ", bold=False)
prideti_run(p8, "Astijus Grinevičius", bold=True)
prideti_run(p8, ",\t\t\tGrupė ", bold=False)
prideti_run(p8, "PI23SN", bold=True)

# [10] Praktikos pavadinimas
p10 = doc.paragraphs[10]
for r in p10.runs:
    r.text = ""
prideti_run(p10, "Praktikos pavadinimas: profesinė / ", bold=False)
prideti_run(p10, "baigiamoji", bold=True, underline=True)
prideti_run(p10, ".", bold=False)
prideti_run(p10, "(tinkamą pabraukti)", bold=False)

# [11] TIKSLAS (paliekam kaip buvo, jei tik uždavinius trumpinam)
p11 = doc.paragraphs[11]
for r in p11.runs:
    r.text = ""
prideti_run(p11, "Tikslas: ", bold=False)
prideti_run(
    p11,
    "Patobulinti ir išplėsti profesinės praktikos metu sukurtą Kupiškio r. "
    "Subačiaus gimnazijos Noriūnų Jono Černiaus skyriaus mokyklos valdymo "
    "informacinę sistemą, pereinant prie produkcinio lygio architektūros, "
    "realizuojant tėvų prieigos portalą, sustiprinant saugumo mechanizmus "
    "bei atliekant sistemos naudojimo tyrimą realioje mokyklos aplinkoje.",
    bold=False
)

# SUTRUMPINTI UŽDAVINIAI (13-16)
uzdaviniai = [
    "Modernizuoti Sistemos architektūrą – atlikti duomenų bazės migraciją į "
    "PostgreSQL, įdiegti Docker konteinerizaciją bei automatinę atsarginių "
    "kopijų sistemą.",

    "Suprojektuoti ir realizuoti tėvų prieigos portalą, leidžiantį pasiekti "
    "vaiko duomenis, mokyklos pranešimus bei komunikuoti su klasės vadovu.",

    "Sustiprinti Sistemos saugumą įdiegus dviejų veiksnių autentikaciją (2FA) "
    "bei realizuoti REST API sąsają mobiliesiems klientams.",

    "Parengti automatinę testavimo sistemą ir atlikti vartotojų patirties "
    "tyrimą Subačiaus gimnazijoje.",
]

for i, uzdavinio_tekstas in enumerate(uzdaviniai):
    p = doc.paragraphs[13 + i]
    for r in p.runs:
        r.text = ""
    prideti_run(p, uzdavinio_tekstas, bold=False)

# [20] Priimančios organizacijos praktikos vadovas
p20 = doc.paragraphs[20]
for r in p20.runs:
    r.text = ""
prideti_run(p20, "Priimančios organizacijos praktikos vadovas ", bold=False)
prideti_run(p20, "Rita Grinevičienė, Noriūnų Jono Černiaus skyriaus vedėja", bold=True)

# [22] EIF praktikos vadovas
p22 = doc.paragraphs[22]
for r in p22.runs:
    r.text = ""
prideti_run(p22, "EIF praktikos vadovas ", bold=False)
prideti_run(p22, "doc. dr. Romanas Tumasonis, lektorius", bold=True)

# [24] Data
p24 = doc.paragraphs[24]
for r in p24.runs:
    r.text = ""
prideti_run(p24, "2026 m. rugsėjo 1 d.", bold=False)

doc.save(NAUJAS)
print(f"✓ Užpildytas dokumentas su SUTRUMPINTAIS uždaviniais išsaugotas.")
print()
print("SUTRUMPINTI UŽDAVINIAI:")
for i, u in enumerate(uzdaviniai, 1):
    print(f"  {i}. {u}")
    print()
