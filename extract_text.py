"""Ištraukia visą ataskaitos tekstą."""
import sys
from docx import Document

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

doc = Document(r'C:\Users\astij\mokyklos-platforma\ataskaita_su_2priedu_FIXED.docx')

isvedimas = []
for p in doc.paragraphs:
    text = p.text
    style = p.style.name
    if text.strip():
        if 'Heading 1' in style:
            isvedimas.append(f'\n\n===== {text} =====\n')
        elif 'Heading 2' in style:
            isvedimas.append(f'\n--- {text} ---\n')
        elif 'Heading 3' in style:
            isvedimas.append(f'\n  *** {text} ***\n')
        else:
            isvedimas.append(text)
    else:
        isvedimas.append('')

# Apsdorot ir lenteles
print('\n'.join(isvedimas[:200]))

# Išsaugot pilną į failą
with open(r'C:\Users\astij\OneDrive\Desktop\ataskaita_tekstas.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(isvedimas))
    f.write('\n\n=== LENTELES ===\n\n')
    for ti, t in enumerate(doc.tables):
        f.write(f'\nLentele {ti + 1}: {len(t.rows)} eil. x {len(t.columns)} stulp.\n')
        for row in t.rows:
            cells = [cell.text.strip() for cell in row.cells]
            f.write(' | '.join(cells) + '\n')
