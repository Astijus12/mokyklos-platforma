"""Automatinis ataskaitos pataisymas - pakeičia poskyrių stilius pagal VIKO reikalavimus.

Logika:
- Heading 1 (1., 2., 3., 4.) - lieka Heading 1 (DIDŽIOSIOS, 14pt)
- Heading 2 (1.1, 1.2, ir t.t.) - poskyriai (mažosios, 14pt)
- Heading 3 (4.5.1, 4.5.2, ir t.t.) - skyreliai (mažosios, 12pt)
"""
import re
import sys
from docx import Document

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\ataskaita_perziurai.docx"
ISTAISYTAS = r"C:\Users\astij\OneDrive\Desktop\Astijus_Grinevicius_PI23SN_Profesines_praktikos_ataskaita_PATAISYTA.docx"


def nustatyti_stiliu(p, naujas_stilius):
    """Pakeičia paragrafo stilių."""
    p.style = p.part.document.styles[naujas_stilius]


doc = Document(ORIGINAL)

# Statistika pakeitimu
stat = {'h2': 0, 'h3': 0}

# Regex pattern'ai
poskyrio_pattern = re.compile(r'^(\d+)\.(\d+)\.\s+\S')  # 1.1., 2.3., ir t.t. (NE 4.5.1.)
skyrelio_pattern = re.compile(r'^(\d+)\.(\d+)\.(\d+)\.\s+\S')  # 4.5.1., 4.5.2.

for p in doc.paragraphs:
    if p.style.name != 'Heading 1':
        continue

    text = p.text.strip()
    if not text:
        continue

    # Skyreliai (3 lygiu numeracija: 4.5.1.) - turi buti pirma, nes irgi tinka poskyrio pattern'ui
    if skyrelio_pattern.match(text):
        nustatyti_stiliu(p, 'Heading 3')
        stat['h3'] += 1
        print(f'  Heading 3: {text[:70]}')
    # Poskyriai (2 lygiu numeracija: 1.1.)
    elif poskyrio_pattern.match(text):
        nustatyti_stiliu(p, 'Heading 2')
        stat['h2'] += 1
        print(f'  Heading 2: {text[:70]}')

print()
print('=' * 60)
print(f'Pakeista į Heading 2 (poskyriai): {stat["h2"]}')
print(f'Pakeista į Heading 3 (skyreliai): {stat["h3"]}')
print(f'Iš viso pakeista: {stat["h2"] + stat["h3"]}')

# Tikrinti, ar Heading 2 ir Heading 3 stiliai turi tinkamus formatus
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

h2 = doc.styles['Heading 2']
h2.font.name = 'Times New Roman'
h2.font.size = Pt(14)
h2.font.bold = True
h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
h2.paragraph_format.line_spacing = 1.0
h2.paragraph_format.space_before = Pt(6)
h2.paragraph_format.space_after = Pt(6)

h3 = doc.styles['Heading 3']
h3.font.name = 'Times New Roman'
h3.font.size = Pt(12)
h3.font.bold = True
h3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
h3.paragraph_format.line_spacing = 1.0
h3.paragraph_format.space_before = Pt(12)
h3.paragraph_format.space_after = Pt(6)

doc.save(ISTAISYTAS)
print()
print(f'✓ Pataisyta ataskaita išsaugota:')
print(f'  {ISTAISYTAS}')
