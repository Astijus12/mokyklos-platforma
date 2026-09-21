"""Pataiso failo Python kodo problemas su lietuviškomis kabutėmis.

Logika: ten kur tekstas turi „ (U+201E) atidaromąjį - pakeičiame visus
po jo einančius " (U+0022) į " (U+201D) iki kol pasiekiama nauja eilutė
arba kita " kabutė už elemento.

Iš tiesų - paprasčiau: pakeičiam visus elementai/layout sąrašus
naudojant Python single-quote outer strings.
"""
import re

with open(r'C:\Users\astij\mokyklos-platforma\paruosti_ataskaita.py', 'rb') as f:
    turinys = f.read().decode('utf-8')

# Mes turim eilutes formatu:
#     "Tekstas su „kažkuo" ir „dar kažkuo".",
#
# Reikia konvertuoti į:
#     'Tekstas su „kažkuo" ir „dar kažkuo".',
#
# Tai padarysim su regex - ieškome eilučių, kurios:
# - Prasideda 4+ tarpais
# - Turi " kaip pradinį ir pabaigos
# - Turi tarp jų „ (U+201E)

# Strategija: einame eilutes po vieną; jei eilutės "..."  turi „ (U+201E),
# konvertuojam outer "..." į '...'

eilutes = turinys.split('\n')
nauja = []
pakeista = 0

for line in eilutes:
    # Tikriname ar eilutė turi „ (U+201E) viduje
    if '„' in line:
        # Bandome rasti pirmąjį " ir paskutinįjį " kaip outer string
        # Bet tik jei eilutė atrodo kaip string literal
        stripped = line.rstrip(',').rstrip()
        # Eilutė turi prasidėti tarpais + " ir baigtis "
        m = re.match(r'^(\s+)"(.*)"(\s*),?$', line)
        if m:
            indent, content, trailing = m.groups()
            # Patikriname, ar content turi „
            if '„' in content:
                # Konvertuojame: outer " į '
                # Inner " (U+0022) turi būti pakeistas į " (U+201D - dešinė kabutė)
                # Bet pirma reikia patikrinti ar nėra esamų ' viduje (būtų problema)
                if "'" not in content:
                    new_content = content.replace('"', '”')
                    naujas_line = f"{indent}'{new_content}'{trailing}"
                    if line.rstrip().endswith(','):
                        naujas_line += ','
                    nauja.append(naujas_line)
                    pakeista += 1
                    continue
    nauja.append(line)

with open(r'C:\Users\astij\mokyklos-platforma\paruosti_ataskaita.py', 'wb') as f:
    f.write('\n'.join(nauja).encode('utf-8'))

print(f"Pakeista eilučių: {pakeista}")
