"""Pataiso priedų struktūrą (Variantas B):
- Pašalina seną painų sąrašą
- Pataiso Ritos pareigas → 'Noriūnų Jono Černiaus skyriaus vedėja'
- Palieka 1 PRIEDĄ (Individuali praktikos užduotis)
- Prideda 2 PRIEDĄ (Sistemos ekrano vaizdai) su vietomis paveikslams
"""
import sys
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

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\ataskaita_priedu_patikra.docx"
NAUJAS = r"C:\Users\astij\mokyklos-platforma\ataskaita_su_2priedu.docx"

doc = Document(ORIGINAL)

# =============================================================================
# 1. RASTI PRIEDAI SEKCIJĄ
# =============================================================================

priedai_pradzia = None
for i, p in enumerate(doc.paragraphs):
    if p.text.strip().upper() == 'PRIEDAI' and p.style.name == 'Heading 1':
        priedai_pradzia = i
        break

print(f"PRIEDAI sekcija: pastraipa [{priedai_pradzia}]")

# =============================================================================
# 2. PAŠALINTI SENĄ SĄRAŠĄ [551-555]
# =============================================================================

# Sąrašas yra po PRIEDAI antraštės iki "1 PRIEDAS." antraštės
saraso_pradzia = priedai_pradzia + 1
saraso_pabaiga = None
for i in range(priedai_pradzia + 1, min(priedai_pradzia + 20, len(doc.paragraphs))):
    if '1 PRIEDAS' in doc.paragraphs[i].text.upper():
        saraso_pabaiga = i - 1
        break

print(f"Senas sąrašas: pastraipos [{saraso_pradzia}] iki [{saraso_pabaiga}]")
print()

# Ištrinti sąrašo pastraipas (atvirkščia tvarka)
to_delete = []
if saraso_pabaiga is not None:
    for i in range(saraso_pradzia, saraso_pabaiga + 1):
        to_delete.append(i)

# Ištrinti per XML
print("Šalinamos pastraipos:")
for i in sorted(to_delete, reverse=True):
    text = doc.paragraphs[i].text[:60]
    print(f"  [{i}] {text}")
    p_element = doc.paragraphs[i]._element
    p_element.getparent().remove(p_element)

print()

# =============================================================================
# 3. PATAISYTI RITOS PAREIGAS
# =============================================================================

print("Pataisomos Ritos Grinevičienės pareigos...")
pakeista_pareigos = 0
for p in doc.paragraphs:
    for run in p.runs:
        if 'direktoriaus pavaduotoja ugdymui' in run.text:
            run.text = run.text.replace(
                'direktoriaus pavaduotoja ugdymui',
                'Noriūnų Jono Černiaus skyriaus vedėja'
            )
            pakeista_pareigos += 1
            print(f"  ✓ Pakeista pareigos")

# =============================================================================
# 4. PRIDĖTI 2 PRIEDĄ (Sistemos ekrano vaizdai)
# =============================================================================

print()
print("Pridedamas 2 PRIEDAS. SISTEMOS EKRANO VAIZDAI...")

# Naujas puslapis
p_break = doc.add_paragraph()
p_break.paragraph_format.first_line_indent = Cm(0)
run = p_break.add_run()
run.add_break(WD_BREAK.PAGE)

# 2 PRIEDAS antraštė - dešinėje, BOLD, 12pt
p_antraste = doc.add_paragraph()
p_antraste.alignment = WD_ALIGN_PARAGRAPH.RIGHT
p_antraste.paragraph_format.first_line_indent = Cm(0)
p_antraste.paragraph_format.space_after = Pt(12)
run = p_antraste.add_run("2 PRIEDAS. SISTEMOS EKRANO VAIZDAI")
run.font.name = "Times New Roman"
run.font.size = Pt(12)
run.font.bold = True

# Įvadinis tekstas
p_intro = doc.add_paragraph()
p_intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p_intro.paragraph_format.first_line_indent = Cm(1.27)
p_intro.paragraph_format.line_spacing = 1.5
run = p_intro.add_run(
    "Šiame priede pateikiami sukurtos mokyklos valdymo informacinės sistemos "
    "ekrano vaizdai, demonstruojantys pagrindines funkcines galimybes. "
    "Sistema pasiekiama internetu, įdiegta Render.com debesijos platformoje."
)
run.font.name = "Times New Roman"
run.font.size = Pt(12)


def prideti_paveikslo_zymeji(doc, numeris, pavadinimas):
    """Prideda paveikslo žymeklį su antrašte."""
    # Pavadinimo placeholder
    p_placeholder = doc.add_paragraph()
    p_placeholder.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_placeholder.paragraph_format.first_line_indent = Cm(0)
    p_placeholder.paragraph_format.space_before = Pt(12)

    placeholder_run = p_placeholder.add_run(
        f"[ČIA ĮDĖTI EKRANO VAIZDĄ: {pavadinimas}]"
    )
    placeholder_run.font.name = "Times New Roman"
    placeholder_run.font.size = Pt(11)
    placeholder_run.italic = True

    # Antraštė po paveikslo
    p_caption = doc.add_paragraph()
    p_caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_caption.paragraph_format.first_line_indent = Cm(0)
    p_caption.paragraph_format.space_after = Pt(12)
    caption_run = p_caption.add_run(f"2P.{numeris} pav. {pavadinimas}")
    caption_run.font.name = "Times New Roman"
    caption_run.font.size = Pt(12)


# Apraso ir paveikslu sąrašas
ekrano_vaizdai = [
    ("1", "Sistemos prisijungimo langas",
     "Sistemos prisijungimo langas su el. pašto ir slaptažodžio laukais. "
     "Apačioje pateikti demonstraciniai prisijungimai administratoriaus ir mokytojo rolėms."),

    ("2", "Pradžios langas (statistinė apžvalga)",
     "Pradžios langas, kuriame pateikiama mokyklos veiklos statistinė apžvalga: "
     "vartotojų skaičius, klasių, mokinių, įkeltų diplomų ir skelbimų bendras kiekis. "
     "Atvaizduojama klasių dydžio diagrama."),

    ("3", "Mokinių sąrašo puslapis",
     "Mokinių sąrašo puslapis su filtravimo ir paieškos galimybėmis. Matomas mokinio "
     "vardas, klasė, žymos (autobusas, gerovės komisija), tėvai bei kontaktiniai duomenys."),

    ("4", "Detalus mokinio profilio puslapis",
     "Mokinio detalus puslapis su asmens duomenimis, tėvų informacija, transportavimo "
     "informacija (mokyklos autobusas) bei vaiko gerovės komisijos sprendimais."),

    ("5", "Mokinio pridėjimo forma",
     "Naujo mokinio pridėjimo forma su pagrindiniais duomenimis, motinos ir tėvo "
     "kontaktais bei papildoma informacija."),

    ("6", "Klasių sąrašo puslapis",
     "Klasių sąrašas, kuriame matomas kiekvienos klasės pavadinimas, mokinių skaičius "
     "bei priskirtas klasės vadovas."),

    ("7", "Diplomų valdymas",
     "Diplomų peržiūros puslapis su įkeltų dokumentų sąrašu, suteikiantis galimybę "
     "peržiūrėti, atsisiųsti ar pašalinti diplomą."),

    ("8", "Skelbimų sąrašas",
     "Mokyklos vidaus skelbimų sąrašas su pavadinimu, autoriumi, data ir svarbumo žyma."),

    ("9", "Globalios paieškos rezultatai",
     "Globalios paieškos puslapis - rezultatai sugrupuoti pagal sritis: mokiniai, klasės, "
     "diplomai, skelbimai."),

    ("10", "Tamsus režimas",
     "Sistemos sąsajos atvaizdavimas tamsiu režimu, pritaikytu komfortabiliam darbui "
     "menko apšvietimo sąlygomis."),
]

# Pridedam kiekvieno paveikslo aprašymą ir vietą
for numeris, pavadinimas, aprasymas in ekrano_vaizdai:
    # Aprašomasis tekstas
    p_aprasymas = doc.add_paragraph()
    p_aprasymas.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_aprasymas.paragraph_format.first_line_indent = Cm(1.27)
    p_aprasymas.paragraph_format.line_spacing = 1.5
    p_aprasymas.paragraph_format.space_before = Pt(12)

    bold_run = p_aprasymas.add_run(f"2P.{numeris} pav. ")
    bold_run.font.name = "Times New Roman"
    bold_run.font.size = Pt(12)
    bold_run.font.bold = True

    desc_run = p_aprasymas.add_run(aprasymas)
    desc_run.font.name = "Times New Roman"
    desc_run.font.size = Pt(12)

    # Vieta paveikslui
    prideti_paveikslo_zymeji(doc, numeris, pavadinimas)

print(f"  ✓ Pridėta 2 PRIEDO antraštė")
print(f"  ✓ Pridėta {len(ekrano_vaizdai)} ekrano vaizdo aprašymų su vietomis")

# =============================================================================
# 5. IŠSAUGOTI
# =============================================================================

doc.save(NAUJAS)
print()
print("=" * 70)
print(f"✓ Pataisyta ataskaita su 2 PRIEDU išsaugota:")
print(f"  {NAUJAS}")
print()
print("ATLIKTI PAKEITIMAI:")
print(f"  1. Pašalintas painus sąrašas po PRIEDAI antraštės")
print(f"  2. Pataisytos Ritos pareigos ({pakeista_pareigos} vietos)")
print(f"  3. Pridėtas 2 PRIEDAS. SISTEMOS EKRANO VAIZDAI")
print(f"     - 10 vietų ekrano vaizdams")
print(f"     - Visos su Times New Roman 12pt, dešinėje, BOLD antraštė")
