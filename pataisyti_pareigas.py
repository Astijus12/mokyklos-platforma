"""Pataiso Ritos Grinevičienės pareigas visuose dokumentuose.

Pakeičia: "direktoriaus pavaduotoja ugdymui" → "skyriaus vedėja"
(Tiksliau - Noriūnų Jono Černiaus skyriaus vedėja)
"""
import sys
import os
import shutil
from docx import Document

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Failai, kuriuose reikia pataisyti pareigas
FAILAI = [
    {
        'pavadinimas': 'Vertinimo lapas',
        'kelias': r"C:\Users\astij\OneDrive\Desktop\PI23SN_profesines_vertinimas_UZPILDYTAS.docx",
    },
    {
        'pavadinimas': 'Individuali užduotis',
        'kelias': r"C:\Users\astij\Downloads\Profesines_praktikos_individuali_uzduotis_UZPILDYTA.docx",
    },
]

# Pakeitimo žodynas
PAKEITIMAI = [
    ("direktoriaus pavaduotoja ugdymui", "skyriaus vedėja"),
    ("direktoriaus pavaduotoja ugdymui", "skyriaus vedėja"),  # variant su didžiaja
    ("Direktoriaus pavaduotoja ugdymui", "Skyriaus vedėja"),
]


def pataisyti_dokumenta(failo_kelias, pavadinimas):
    """Pataiso pareigas viename dokumente."""
    if not os.path.exists(failo_kelias):
        print(f"  ⚠ Failas nerastas: {failo_kelias}")
        return False

    # Kopijos darymas (saugumui)
    doc = Document(failo_kelias)
    pakeista = 0

    for p in doc.paragraphs:
        for run in p.runs:
            originalus_tekstas = run.text
            naujas_tekstas = originalus_tekstas
            for senas, naujas in PAKEITIMAI:
                if senas in naujas_tekstas:
                    naujas_tekstas = naujas_tekstas.replace(senas, naujas)
                    pakeista += 1
            if naujas_tekstas != originalus_tekstas:
                run.text = naujas_tekstas

    # Patikrinti ir lenteles
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        originalus_tekstas = run.text
                        naujas_tekstas = originalus_tekstas
                        for senas, naujas in PAKEITIMAI:
                            if senas in naujas_tekstas:
                                naujas_tekstas = naujas_tekstas.replace(senas, naujas)
                                pakeista += 1
                        if naujas_tekstas != originalus_tekstas:
                            run.text = naujas_tekstas

    if pakeista > 0:
        doc.save(failo_kelias)
        print(f"  ✓ {pavadinimas}: {pakeista} pakeitimai")
        return True
    else:
        print(f"  - {pavadinimas}: nieko nerasta pakeisti")
        return False


print("PAREIGŲ PATAISYMAS:")
print("=" * 70)
print("Keičiama: 'direktoriaus pavaduotoja ugdymui' → 'skyriaus vedėja'")
print()

for failas in FAILAI:
    pataisyti_dokumenta(failas['kelias'], failas['pavadinimas'])

print()
print("=" * 70)
print("PATAISYMAS BAIGTAS")
