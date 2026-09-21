"""Sutvarko priedus ataskaitoje pagal VIKO reikalavimus.

Veiksmai:
1. Suranda "PRIEDAI" sekciją
2. Pridėją "1 PRIEDAS. INDIVIDUALI PRAKTIKOS UŽDUOTIS" antraštę
   (12pt Bold, DIDŽIOSIOS raidės, lygiavimas DEŠINĖJE)
3. Įterpia visą Individualios užduoties turinį (paimtą iš užpildyto failo)
4. Pradeda naujame puslapyje
"""
import sys
from copy import deepcopy
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\ataskaita_su_lentelemis.docx"
UZDUOTIES_FAILAS = r"C:\Users\astij\Downloads\Profesines_praktikos_individuali_uzduotis_UZPILDYTA.docx"
ISTAISYTAS = r"C:\Users\astij\mokyklos-platforma\ataskaita_su_priedais.docx"

doc = Document(ORIGINAL)
uzduotis = Document(UZDUOTIES_FAILAS)


def prideti_priedo_antraste(doc, numeris, pavadinimas):
    """Prideda priedo antraštę (12pt Bold DIDŽIOSIOMIS, dešinėje)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(12)  # 12pt tarpas po antrašte

    tekstas = f"{numeris} PRIEDAS. {pavadinimas.upper()}"
    run = p.add_run(tekstas)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = True

    # XML lygiu nustatyti šriftą
    rpr = run._r.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), "Times New Roman")
    rfonts.set(qn("w:hAnsi"), "Times New Roman")
    rfonts.set(qn("w:eastAsia"), "Times New Roman")
    return p


def prideti_puslapio_luzti(doc):
    """Prideda puslapio lūžį."""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run()
    run.add_break(WD_BREAK.PAGE)


def kopijuoti_pastraipu_turini(p_šaltinis, p_tikslas):
    """Kopijuoja pastraipos turinio (run'ų) iš vieno paragrafo į kitą."""
    for run in p_šaltinis.runs:
        new_run = p_tikslas.add_run(run.text)
        new_run.font.name = run.font.name or "Times New Roman"
        if run.font.size:
            new_run.font.size = run.font.size
        else:
            new_run.font.size = Pt(12)
        new_run.font.bold = run.font.bold
        new_run.font.italic = run.font.italic
        new_run.font.underline = run.font.underline


# =============================================================================
# 1. PRIDĖTI PUSLAPIO LŪŽĮ ATASKAITOS PABAIGOJE (po PRIEDAI sąrašo)
# =============================================================================

print("Pridedamas puslapio lūžis prieš 1 PRIEDĄ...")
prideti_puslapio_luzti(doc)

# =============================================================================
# 2. PRIDĖTI 1 PRIEDO ANTRAŠTĘ
# =============================================================================

print("Pridedama 1 PRIEDAS antraštė...")
prideti_priedo_antraste(doc, "1", "Individuali praktikos užduotis")

# =============================================================================
# 3. ĮTERPTI INDIVIDUALIOS UŽDUOTIES TURINĮ
# =============================================================================

print("Įterpiamas Individualios užduoties turinys...")
print()

# Pereikim per visus užduoties paragrafus ir nukopijuokim juos
# Pirmasis paragrafas užduoties faile yra "2 PRIEDAS. INDIVIDUALI PRAKTIKOS UŽDUOTIS"
# - jį praleidžiame, nes mes patys pridėjome teisinga "1 PRIEDAS." antraštę

skip_first_heading = True
imported_count = 0

for p_šaltinis in uzduotis.paragraphs:
    text = p_šaltinis.text.strip()

    # Praleisti pirmąją "2 PRIEDAS..." antraštę
    if skip_first_heading and "PRIEDAS" in text:
        skip_first_heading = False
        print(f"  [SKIP] Praleidžiama: {text[:60]}")
        continue

    # Sukurkim naują paragrafą pagrindinio dokumento gale
    p_tikslas = doc.add_paragraph()
    p_tikslas.alignment = p_šaltinis.alignment
    p_tikslas.paragraph_format.line_spacing = p_šaltinis.paragraph_format.line_spacing
    p_tikslas.paragraph_format.first_line_indent = Cm(0)
    p_tikslas.paragraph_format.space_before = Pt(0)
    p_tikslas.paragraph_format.space_after = Pt(6)

    # Kopijuoti turinį
    kopijuoti_pastraipu_turini(p_šaltinis, p_tikslas)

    if text:
        imported_count += 1
        preview = text[:60] + ("..." if len(text) > 60 else "")
        print(f"  [+] Įdėta: {preview}")

print()
print("=" * 70)
print(f"Įterpta pastraipų iš užduoties: {imported_count}")
print()

doc.save(ISTAISYTAS)
print(f"✓ Dokumentas su priedais išsaugotas:")
print(f"  {ISTAISYTAS}")
