"""Automatinis lentelių formatavimo taisymas pagal VIKO reikalavimus.

Taisoma:
1. Šriftas - Times New Roman 12pt nepastorinta
2. Tarpas tarp eilučių - Single (1.0)
3. Repeat Header Row - antraštės kartojasi kituose puslapiuose
4. Pirmojo stulpelio lygiavimas - kairėje
5. Antraštės eilutės tekstas - Bold + Center
"""
import sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\ataskaita_galutinis_su_antrastemis.docx"
ISTAISYTAS = r"C:\Users\astij\mokyklos-platforma\ataskaita_su_lentelemis.docx"

doc = Document(ORIGINAL)


def nustatyti_pirmos_eilutes_kartojimo(table):
    """Įjungia 'Repeat Header Row' - antraštė kartojasi kiekviename puslapyje."""
    first_row = table.rows[0]
    trPr = first_row._tr.get_or_add_trPr()

    # Patikriname, ar jau yra tblHeader
    existing = trPr.find(qn('w:tblHeader'))
    if existing is None:
        tbl_header = OxmlElement('w:tblHeader')
        tbl_header.set(qn('w:val'), 'true')
        trPr.append(tbl_header)


def nustatyti_sriftai_celeje(cell, bold=False, size=12, align=None):
    """Nustato celės teksto formatą."""
    for paragraph in cell.paragraphs:
        if align is not None:
            paragraph.alignment = align
        # Single tarpas tarp eilučių
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.first_line_indent = Cm(0)

        for run in paragraph.runs:
            run.font.name = 'Times New Roman'
            run.font.size = Pt(size)
            if bold:
                run.font.bold = True

            # XML lygiu
            rpr = run._r.get_or_add_rPr()
            rfonts = rpr.find(qn('w:rFonts'))
            if rfonts is None:
                rfonts = OxmlElement('w:rFonts')
                rpr.insert(0, rfonts)
            rfonts.set(qn('w:ascii'), 'Times New Roman')
            rfonts.set(qn('w:hAnsi'), 'Times New Roman')
            rfonts.set(qn('w:eastAsia'), 'Times New Roman')


print("LENTELĖS FORMATAVIMO TAISYMAS:")
print("=" * 70)

stat = {'lenteles': 0, 'celes': 0, 'eiluciu_su_antraste': 0}

for t_idx, table in enumerate(doc.tables):
    stat['lenteles'] += 1
    print(f"\nLENTELĖ #{t_idx + 1}: {len(table.rows)} eilučių × {len(table.columns)} stulpelių")

    # 1. Įjungti antraštės kartojimą puslapiuose
    nustatyti_pirmos_eilutes_kartojimo(table)
    stat['eiluciu_su_antraste'] += 1
    print("  ✓ Repeat Header Row įjungtas")

    # 2. Formuoti pirmą eilutę (antraštę) - Bold + Center
    header_row = table.rows[0]
    for cell in header_row.cells:
        nustatyti_sriftai_celeje(
            cell,
            bold=True,
            size=12,
            align=WD_ALIGN_PARAGRAPH.CENTER
        )
        stat['celes'] += 1
    print(f"  ✓ Antraštė: Bold + Center ({len(header_row.cells)} celių)")

    # 3. Formuoti likusias eilutes
    for row_idx, row in enumerate(table.rows[1:], 1):
        for col_idx, cell in enumerate(row.cells):
            # Pirmas stulpelis - kairėje, kiti - kairėje (per requirements)
            if col_idx == 0:
                align = WD_ALIGN_PARAGRAPH.LEFT
            else:
                align = WD_ALIGN_PARAGRAPH.LEFT  # Galima ir CENTER

            nustatyti_sriftai_celeje(
                cell,
                bold=False,
                size=12,
                align=align
            )
            stat['celes'] += 1
    print(f"  ✓ Duomenų eilučių: {len(table.rows) - 1}")

print()
print("=" * 70)
print(f"ATLIKTA:")
print(f"  Lentelių apdorota:           {stat['lenteles']}")
print(f"  Celių formatuota:             {stat['celes']}")
print(f"  Antraščių kartosis puslapiuose: {stat['eiluciu_su_antraste']}")

doc.save(ISTAISYTAS)
print()
print(f"✓ Dokumentas su pataisytomis lentelėmis išsaugotas:")
print(f"  {ISTAISYTAS}")
