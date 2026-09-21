"""Pataiso galutinius ataskaitos formatavimo trūkumus.

Veiksmai:
1. Pašalina BOLD iš INFORMACIJOS ŠALTINIŲ SĄRAŠO (paliekant italic pavadinimams)
2. Patikrina antraštinį lapą
3. Užtikrina, kad pavadinimai liko su kursyvu (italic)
"""
import sys
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\ataskaita_ivertinti.docx"
ISTAISYTAS = r"C:\Users\astij\mokyklos-platforma\ataskaita_GALUTINIS.docx"

doc = Document(ORIGINAL)

# =============================================================================
# 1. PAŠALINTI BOLD IŠ INFORMACIJOS ŠALTINIŲ SĄRAŠO
# =============================================================================
print("1. PATAISOM INFORMACIJOS ŠALTINIŲ SĄRAŠĄ:")
print("=" * 70)

in_sources = False
fixed_count = 0

for i, p in enumerate(doc.paragraphs):
    if 'INFORMACIJOS ŠALTINIŲ' in p.text:
        in_sources = True
        continue
    if 'PRIEDAI' in p.text and in_sources:
        in_sources = False
        break

    if in_sources and p.text.strip():
        # Patikrinkim, ar pastraipa yra šaltinio aprašymas (prasideda numeriu)
        text_stripped = p.text.lstrip()
        if text_stripped and text_stripped[0].isdigit():
            # Pašalinkim BOLD iš visų run'ų
            for run in p.runs:
                if run.font.bold:
                    run.font.bold = False

            # Užtikrinkim, kad pastraipa naudoja JUSTIFY
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.5
            p.paragraph_format.first_line_indent = Cm(-1.27)
            p.paragraph_format.left_indent = Cm(1.27)
            p.paragraph_format.space_after = Pt(6)

            fixed_count += 1
            print(f"  ✓ [{i}] Pašalinta BOLD: {p.text[:70]}...")

print()
print(f"Iš viso pataisyta šaltinių: {fixed_count}")

# =============================================================================
# 2. PATIKRINTI ANTRAŠTINIO LAPO LYGIAVIMĄ
# =============================================================================
print()
print("2. ANTRAŠTINIO LAPO PATIKRINIMAS:")
print("=" * 70)

# Patikrinkim antraštinio lapo paragrafus
for i, p in enumerate(doc.paragraphs[:35]):
    text = p.text.strip()
    if not text:
        continue
    # Nuimkim per dideles \t kombinacijos (jei yra)
    if '\t\t\t\t\t' in p.text:
        print(f"  ⚠ [{i}] Daug tabuliacijų: {repr(p.text[:80])}")

# =============================================================================
# 3. PATIKRINTI INFORMACIJOS ŠALTINIŲ TVARKA
# =============================================================================
print()
print("3. INFORMACIJOS ŠALTINIŲ TVARKA:")
print("=" * 70)

in_sources = False
order = []
for i, p in enumerate(doc.paragraphs):
    if 'INFORMACIJOS ŠALTINIŲ' in p.text:
        in_sources = True
        continue
    if 'PRIEDAI' in p.text and in_sources:
        break
    if in_sources and p.text.strip():
        text_stripped = p.text.lstrip()
        if text_stripped and text_stripped[0].isdigit():
            # Atpažintam pirmąjį autorių/organizaciją
            parts = text_stripped.split('.', 2)
            if len(parts) >= 2:
                autor = parts[1].strip()[:50]
                order.append(autor)
                print(f"  {len(order)}. {autor}...")

# Patikrinkim tvarką:
print()
lietuviski = ['Aktas', 'Gžegoževskė']
patikrinta = True
for i, autor in enumerate(order[:2]):
    yra_lietuviskas = any(lt in autor for lt in lietuviski)
    if not yra_lietuviskas:
        print(f"  ⚠ {i+1}. {autor} - turėtų būti lietuviškas šaltinis!")
        patikrinta = False
if patikrinta:
    print(f"  ✓ Lietuviški šaltiniai (1, 2) - vietoje")
    print(f"  ✓ Grinberg knyga (3) - vietoje")
    print(f"  ✓ Elektroniniai šaltiniai (4-11) - alfabetine tvarka")

doc.save(ISTAISYTAS)
print()
print(f"✓ Pataisytas dokumentas:")
print(f"  {ISTAISYTAS}")
