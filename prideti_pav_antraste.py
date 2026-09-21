"""Prideda trūkstamas paveikslų antraštes (1-4 pav. UML diagramoms).

Pagal Bendrųjų reikalavimų - paveikslų antraštės rašomos PO paveikslu,
Times New Roman 12pt, nepastorinta, centruotos.
"""
import sys
from copy import deepcopy
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

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\ataskaita_galutinis_caption.docx"
ISTAISYTAS = r"C:\Users\astij\mokyklos-platforma\ataskaita_galutinis_su_antrastemis.docx"

doc = Document(ORIGINAL)

# Pirmiausia patikrinkim, kuriose pastraipose yra paveikslai
print("PAVEIKSLŲ PASKIRSTYMAS:")
print("=" * 70)

paveikslu_pastraipos = []
for i, p in enumerate(doc.paragraphs):
    drawings = p._element.findall('.//' + qn('w:drawing'))
    if drawings:
        prev_text = doc.paragraphs[i-1].text[:60] if i > 0 else ''
        next_text = doc.paragraphs[i+1].text[:60] if i < len(doc.paragraphs)-1 else ''
        paveikslu_pastraipos.append({
            'idx': i,
            'prev': prev_text,
            'next': next_text,
            'count': len(drawings)
        })
        print(f"  [{i}] Paveikslų skaičius: {len(drawings)}")
        print(f"      Prev: {prev_text}")
        print(f"      Next: {next_text}")
        print()

# Priskirsim antraštes pagal paveikslų kontekstą
# Atmetam antraštinio lapo logotipą (indeksas 0)
print()
print("PRISKIRTOS ANTRAŠTĖS:")
print("=" * 70)

# Antraštės pagal numerį ir kontekstą
PAVEIKSLU_ANTRASTES = {
    1: "1 pav. Sistemos panaudos atvejų diagrama",
    2: "2 pav. Mokinio pridėjimo veiklos diagrama",
    3: "3 pav. Vartotojo autentikacijos sekos diagrama",
    4: "4 pav. Sistemos esybių–ryšių diagrama",
}


def turi_antraste_po(doc, idx):
    """Patikrina, ar po šio paveikslo iš karto eina paveikslo antraštė."""
    # Tikrinam kelias kitas pastraipas (gali būti tuščia eilutė tarp)
    for j in range(idx + 1, min(idx + 4, len(doc.paragraphs))):
        text = doc.paragraphs[j].text.strip()
        if not text:
            continue
        if text.lower().startswith(('1 pav', '2 pav', '3 pav', '4 pav', '5 pav', '6 pav')):
            return True
        # Jei tiesiog tekstas - antraštės dar nėra
        return False
    return False


def prideti_antraste_po_paveikslo(doc, paveikslo_idx, antrastes_tekstas):
    """Įterpia paveikslo antraštę POPaveikslo XML lygiu."""
    # Sukuriam naują pastraipą su Caption stiliumi
    paveikslo_p = doc.paragraphs[paveikslo_idx]

    # Sukurkim naują pastraipos XML
    nauja_p = OxmlElement('w:p')

    # Pridėkim pastraipos savybes - Caption stilių
    pPr = OxmlElement('w:pPr')
    pStyle = OxmlElement('w:pStyle')
    pStyle.set(qn('w:val'), 'Caption')
    pPr.append(pStyle)
    nauja_p.append(pPr)

    # Pridėkim teksto runą
    nauja_r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    rPr.append(rFonts)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), '24')  # 24 half-points = 12pt
    rPr.append(sz)
    # Pašalinam bold/italic eksplicitai
    b_off = OxmlElement('w:b')
    b_off.set(qn('w:val'), '0')
    rPr.append(b_off)
    nauja_r.append(rPr)

    t = OxmlElement('w:t')
    t.text = antrastes_tekstas
    nauja_r.append(t)

    nauja_p.append(nauja_r)

    # Įdėkim po paveikslo pastraipos
    paveikslo_p._element.addnext(nauja_p)


# Apdorojam paveikslus, praleisdami antraštinį lapo logotipą
pav_numeris = 0
trukstami = []

for pav_info in paveikslu_pastraipos:
    idx = pav_info['idx']

    # Atmetam antraštinio lapo logotipą (idx=0)
    if idx == 0:
        print(f"  [SKIP] [{idx}] Antraštinio lapo logotipas - antraštės nereikia")
        continue

    pav_numeris += 1

    # Patikrinam, ar antraštė jau yra
    if turi_antraste_po(doc, idx):
        print(f"  [OK]   [{idx}] {pav_numeris} pav. - antraštė jau yra")
        continue

    # Jei nepriklauso prie 1-4 numerių (gali būti per daug paveikslų)
    if pav_numeris not in PAVEIKSLU_ANTRASTES:
        print(f"  [?]    [{idx}] Nežinau, kokia antraštė turi būti")
        continue

    antraste = PAVEIKSLU_ANTRASTES[pav_numeris]
    prideti_antraste_po_paveikslo(doc, idx, antraste)
    trukstami.append((idx, antraste))
    print(f"  [NEW]  [{idx}] Pridėta antraštė: {antraste}")

print()
print("=" * 70)
print(f"Iš viso pridėta antraščių: {len(trukstami)}")

doc.save(ISTAISYTAS)
print()
print(f"✓ Dokumentas su antraštėmis išsaugotas:")
print(f"  {ISTAISYTAS}")
