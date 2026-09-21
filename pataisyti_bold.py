"""Smart BOLD pataisymas - nuima BOLD iš netinkamų vietų, palieka kur reikia.

Logika:
- TITLE PAGE (pirmosios ~40 pastraipų, Normal style) - palieka BOLD (VIKO reikalavimas)
- TEKSTAS body paragraphs - jei yra lead-in (pirmas run ends with "–" or ".")
  palieka BOLD tik ant lead-in, kitur nuima
- LENTELE style (lentelių antraštės) - nuima BOLD (Caption stilius)
- TABLE OF FIGURES style (paveikslų/lentelių sąrašas) - nuima BOLD
- HEADING 1/2/3 - palieka BOLD (skyrių antraštės)
- TOC entries (Normal po antraštinio lapo) - palieka BOLD (VIKO reikalavimas)
- LIST PARAGRAPH - nuima BOLD jei tai išvados/sąrašai

Lentelių pirma eilutė (antraštė) - palieka BOLD
"""
import sys
import re
from docx import Document

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ORIGINAL = r"C:\Users\astij\mokyklos-platforma\ataskaita_GALUTINIS.docx"
ISTAISYTAS = r"C:\Users\astij\mokyklos-platforma\ataskaita_GALUTINIS_v2.docx"

doc = Document(ORIGINAL)

# Statistika
stat = {
    'paliktas_tekstas_lead_in': 0,
    'nuimtas_tekstas_visas': 0,
    'nuimta_lentele': 0,
    'nuimta_paveikslu_sarasas': 0,
    'palikta_normal_titulinis': 0,
    'palikta_heading': 0,
}


def ar_lead_in(text):
    """Patikrina, ar tekstas atrodo kaip lead-in (trumpa frazė su .)."""
    if not text:
        return False
    text = text.strip()
    if len(text) > 40:
        return False
    # Įvado lead-ins
    if re.match(r'^[A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž\s]+\.\s*$', text):
        return True
    # Terminologijos: "API – ", "SQL – ", "MVC – ", etc.
    if re.match(r'^[A-ZĄČĘĖĮŠŲŪŽ]{1,10}\s*–\s*$', text):
        return True
    if re.match(r'^[A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž]+\s*–\s*$', text):
        return True
    return False


def yra_terminologijos_eilute(p_text):
    """Patikrina, ar TEKSTAS pastraipa yra terminų sąrašo eilutė."""
    # Pattern: "TERM – "
    return bool(re.match(r'^[A-ZĄČĘĖĮŠŲŪŽa-z]{1,15}\s+–\s+', p_text))


def yra_ivado_lead_in_pastraipa(p_text):
    """Patikrina, ar TEKSTAS pastraipa prasideda lead-in fraze su tasku."""
    # Pattern: "Temos aktualumas. ..." arba "Problema. ..."
    return bool(re.match(r'^[A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž\s]{2,30}\.\s+\S', p_text))


print("BOLD PATAISYMAS:")
print("=" * 70)

for i, p in enumerate(doc.paragraphs):
    if not p.text.strip():
        continue

    style_name = p.style.name
    text = p.text

    # 1. TITLE PAGE (Normal stilius, indeksai 0-38)
    if i < 40 and style_name == 'Normal':
        # Palieka BOLD - antraštinis lapas
        stat['palikta_normal_titulinis'] += 1
        continue

    # 2. HEADING stiliai - palikti BOLD
    if 'Heading' in style_name:
        stat['palikta_heading'] += 1
        continue

    # 3. LENTELE stilius (lentelių antraštės) - nuimti BOLD
    if style_name == 'lentele':
        for run in p.runs:
            run.font.bold = False
        stat['nuimta_lentele'] += 1
        continue

    # 4. CAPTION stilius - nuimti BOLD
    if style_name == 'Caption':
        for run in p.runs:
            run.font.bold = False
        stat['nuimta_lentele'] += 1
        continue

    # 5. TABLE OF FIGURES stilius - nuimti BOLD
    if style_name == 'table of figures':
        for run in p.runs:
            run.font.bold = False
        stat['nuimta_paveikslu_sarasas'] += 1
        continue

    # 6. TEKSTAS stilius - smart lead-in detekcija
    if style_name == 'TEKSTAS':
        # Terminologijos pastraipa (API – ...)
        if yra_terminologijos_eilute(text):
            # Surasti " – " poziciją
            idx_dash = text.find(' – ')
            if idx_dash > 0:
                term_dalis = text[:idx_dash + 3]  # "API – "
                # Eikim per runs, žiūrim kuriame run baigiasi term_dalis
                cumulative = ''
                lead_in_baigtas = False
                for run in p.runs:
                    cumulative += run.text
                    if not lead_in_baigtas:
                        if len(cumulative) <= len(term_dalis):
                            run.font.bold = True
                        else:
                            # Šiame run pasibaigė lead-in - keičiam dalimis
                            # Bet runs negalima pakeisti dalimis lengvai
                            # Tiesiog paliekam šį run NE-bold
                            run.font.bold = False
                            lead_in_baigtas = True
                    else:
                        run.font.bold = False
                stat['paliktas_tekstas_lead_in'] += 1
                continue

        # Įvado lead-in pastraipa (Temos aktualumas. ...)
        if yra_ivado_lead_in_pastraipa(text):
            # Surasti pirmą "." poziciją
            idx_dot = text.find('.')
            if idx_dot > 0:
                lead_in_dalis = text[:idx_dot + 1]  # "Temos aktualumas."
                cumulative = ''
                lead_in_baigtas = False
                for run in p.runs:
                    cumulative += run.text
                    if not lead_in_baigtas:
                        if len(cumulative) <= len(lead_in_dalis) + 1:
                            run.font.bold = True
                        else:
                            run.font.bold = False
                            lead_in_baigtas = True
                    else:
                        run.font.bold = False
                stat['paliktas_tekstas_lead_in'] += 1
                continue

        # Normalus TEKSTAS - nuimti BOLD
        for run in p.runs:
            run.font.bold = False
        stat['nuimtas_tekstas_visas'] += 1
        continue

    # 7. LIST PARAGRAPH - nuimti BOLD
    if style_name == 'List Paragraph':
        for run in p.runs:
            run.font.bold = False
        continue

    # 8. Normal po antraštinio lapo - TOC, sąrašai
    if style_name == 'Normal':
        # TOC entries turi būti BOLD pagal VIKO reikalavimus
        # Bet jei tai paprasta sąrašo eilutė kaip "1. ..." - palikti
        if text.lstrip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            # Sąrašo eilutė (gali būti TOC) - tikrinam
            # Jei tai INFORMACIJOS ŠALTINIŲ SĄRAŠAS - jau pataisyta
            # Kitur palikim
            continue
        continue

# =============================================================================
# 9. LENTELIŲ ANTRAŠTĖS - patikrinti, kad pirma eilutė liko BOLD
# =============================================================================

print()
print("Tikrinam lentelių antraščių eilutes...")
table_count = 0
for table in doc.tables:
    if not table.rows:
        continue
    # Pirma eilutė - turi būti BOLD
    for cell in table.rows[0].cells:
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.bold = True
    table_count += 1
print(f"  ✓ {table_count} lentelių antraštės palikta BOLD")

# =============================================================================
# REZULTATAI
# =============================================================================
print()
print("=" * 70)
print("REZULTATAI:")
print(f"  Antraštinio lapo BOLD palikta:       {stat['palikta_normal_titulinis']}")
print(f"  Heading 1/2/3 BOLD palikta:          {stat['palikta_heading']}")
print(f"  TEKSTAS lead-in BOLD palikta:        {stat['paliktas_tekstas_lead_in']}")
print(f"  TEKSTAS body BOLD nuimta:            {stat['nuimtas_tekstas_visas']}")
print(f"  Lentelių antraščių BOLD nuimta:      {stat['nuimta_lentele']}")
print(f"  Paveikslų sąrašo BOLD nuimta:        {stat['nuimta_paveikslu_sarasas']}")

doc.save(ISTAISYTAS)
print()
print(f"✓ Dokumentas išsaugotas:")
print(f"  {ISTAISYTAS}")
