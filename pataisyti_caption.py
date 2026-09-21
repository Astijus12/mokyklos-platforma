"""Automatinis Caption stiliaus pataisymas - visoms lentelių ir paveikslų antraštėms.

Logika:
1. Nustato Caption stilių pagal VIKO reikalavimus
   (Times New Roman 12pt, centruota, ne bold, ne italic)
2. Suranda visas antraštes (X pav. ... arba X lentelė. ...)
3. Pakeičia jų stilių į Caption
"""
import re
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

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\ataskaita_pataisyti_caption.docx"
ISTAISYTAS = r"C:\Users\astij\mokyklos-platforma\ataskaita_galutinis_caption.docx"

doc = Document(ORIGINAL)

# =============================================================================
# 1. NUSTATOM CAPTION STILIŲ
# =============================================================================
caption = doc.styles['Caption']
caption.font.name = 'Times New Roman'
caption.font.size = Pt(12)
caption.font.bold = False
caption.font.italic = False
caption.font.color.rgb = RGBColor(0, 0, 0)  # Juoda spalva

# XML lygiu nustatom šriftą (kad veiktų visiems Unicode simboliams)
rpr = caption.element.get_or_add_rPr()
rfonts = rpr.find(qn("w:rFonts"))
if rfonts is None:
    rfonts = OxmlElement("w:rFonts")
    rpr.insert(0, rfonts)
rfonts.set(qn("w:ascii"), "Times New Roman")
rfonts.set(qn("w:hAnsi"), "Times New Roman")
rfonts.set(qn("w:eastAsia"), "Times New Roman")
rfonts.set(qn("w:cs"), "Times New Roman")

# Pastraipos formatas
caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
caption.paragraph_format.line_spacing = 1.5
caption.paragraph_format.space_before = Pt(6)
caption.paragraph_format.space_after = Pt(6)
caption.paragraph_format.first_line_indent = Cm(0)

print("✓ Caption stilius nustatytas:")
print("  Šriftas:     Times New Roman 12pt")
print("  Storis:      ne Bold")
print("  Kursyvas:    ne Italic")
print("  Lygiavimas:  Centruotas")
print("  Tarpas:      1.5 eilutės")
print("  Įtrauka:     0 cm")
print()

# =============================================================================
# 2. ATPAŽINSTAM VISAS ANTRAŠTES PAGAL TEKSTO ŠABLONUS
# =============================================================================
# Pavyzdys: "1 lentelė. Pagrindinės..." arba "2.1 pav. ..."

lenteles_pattern = re.compile(r'^\d+(\.\d+)?\s*lentel[ėe]\.\s+\S', re.IGNORECASE)
paveikslo_pattern = re.compile(r'^\d+(\.\d+)?\s*pav\.\s+\S', re.IGNORECASE)

print("ATPAŽINTOS ANTRAŠTĖS:")
print("=" * 70)

stat = {'lenteles': 0, 'paveikslai': 0}

for i, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    if not text:
        continue

    if lenteles_pattern.match(text):
        old_style = p.style.name
        p.style = doc.styles['Caption']
        stat['lenteles'] += 1
        print(f"  [LENT] [{i}] (buvo: {old_style}) → Caption")
        print(f"         {text[:80]}")
    elif paveikslo_pattern.match(text):
        old_style = p.style.name
        p.style = doc.styles['Caption']
        stat['paveikslai'] += 1
        print(f"  [PAV]  [{i}] (buvo: {old_style}) → Caption")
        print(f"         {text[:80]}")

print()
print("=" * 70)
print(f"VISO PAKEISTA Į CAPTION STILIŲ:")
print(f"  Lentelių antraščių:    {stat['lenteles']}")
print(f"  Paveikslų antraščių:   {stat['paveikslai']}")
print(f"  Iš viso:               {stat['lenteles'] + stat['paveikslai']}")

doc.save(ISTAISYTAS)
print()
print(f"✓ Galutinis dokumentas išsaugotas:")
print(f"  {ISTAISYTAS}")
