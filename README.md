# Mokyklos administracinių procesų automatizavimo sistema

Noriūnų Jono Černiaus mokyklos internetinė sistema darbuotojams ir tėvams. Baigiamojo darbo
(VIKO, 2026–2027 m.) metu ji papildyta keturiais moduliais: Vaiko gerovės komisijos veikla,
automatiniai pranešimai pagal taisykles, dokumentų generavimas ir masinis mokinių bei tėvų importas.

## Technologijos

- Python 3.12 arba naujesnis, Flask 3.1, SQLAlchemy, Flask-Migrate (Alembic), Flask-Login, Flask-WTF (CSRF apsauga)
- PostgreSQL (Docker – 16 versija); SQLite naudojamas tik greitiems testams
- APScheduler 3.11 – fono procesas (pranešimų siuntimas, priminimai, mėnesio suvestinė)
- ReportLab – PDF dokumentai; openpyxl – XLSX importas ir eksportas; Jinja2 SandboxedEnvironment – pranešimų šablonai
- Tailwind CSS, Lucide ikonos; pytest, pytest-cov

## Moduliai

| Modulis | Kas jame yra | Kas naudoja |
|---------|--------------|-------------|
| Mokiniai, klasės, skelbimai, kalendorius, diplomai | Sukurta praktikų metu | Darbuotojai |
| Tėvų portalas | Vaikų duomenys, skelbimai, renginiai, pažymų užsakymas | Tėvai |
| Vaiko gerovės komisija | Kreipimaisi, atvejai, posėdžiai su 5 darbo dienų patikra, kvietimai, nutarimai, priemonės, protokolai | Komisijos nariai, darbuotojai |
| Automatizavimas | Įvykiai, taisyklės, pranešimų eilė, el. paštas ir pranešimų centras, šablonai, siuntimo žurnalas | Administratorius, visi gavėjai |
| Dokumentai | Pažymos, posėdžių protokolai, ataskaitos su numeriais ir SHA-256 kontroline suma, registras | Administratorius, tėvai |
| Duomenų importas | XLSX ir CSV tikrinimas, peržiūra, įrašymas viena transakcija, tėvų paskyros su kvietimais | Administratorius |

## Projekto struktūra

```
mokyklos-platforma/
├── app.py                # Programos kūrimas, maršrutų registravimas, CSRF apsauga
├── wsgi.py               # Gunicorn įėjimo taškas: migracijos ir demonstraciniai duomenys
├── worker.py             # Fono procesas (APScheduler planuoklė)
├── db_atnaujinimas.py    # Schemos atnaujinimas (tinka ir senai duomenų bazei be migracijų)
├── config.py             # Nustatymai (.env, el. paštas, dokumentai)
├── seed.py               # Demonstraciniai duomenys
├── models/               # Duomenų modeliai: 9 praktikų ir 14 baigiamojo darbo lentelių
├── services/             # Paslaugų sluoksnis: VGK, įvykiai, taisyklės, eilė, kanalai, šablonai,
│                         # priminimai, dokumentai, pažymos, importas, paskyros, planuoklė
├── routes/               # Maršrutai (nauji: vgk, automatizavimas, dokumentai, importas)
├── templates/            # Jinja2 šablonai
├── static/               # CSS, JavaScript, įkelti failai
├── migrations/versions/  # Alembic migracijos 0001–0005
├── scripts/              # Duomenų bazės kūrimas, atsarginės kopijos, matavimai
├── tests/                # pytest testai; tests/postgres – testai, kuriems reikia PostgreSQL
├── Dockerfile
└── docker-compose.yml    # web, worker, db (PostgreSQL 16), backup
```

## Paleidimas su Docker

```powershell
docker compose up --build
```

Sistema pasiekiama adresu http://localhost:8000. Paleidžiant automatiškai įvykdomos migracijos, o
tuščioje duomenų bazėje sukuriami demonstraciniai duomenys. Kintamuosius (slaptasis raktas,
el. pašto serveris) galima nurodyti faile `.env` – pavyzdys `.env.example`. Be el. pašto serverio
laiškai neišsiunčiami, o įrašomi kaip `.eml` failai į katalogą `duomenys/laiskai`.

## Paleidimas be Docker (Windows)

1. Virtuali aplinka ir paketai:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. PostgreSQL naudotojas ir duomenų bazės (vieną kartą):
   ```powershell
   & "C:\Program Files\PostgreSQL\19\bin\psql.exe" -U postgres -f scripts\sukurti_duomenu_baze.sql
   ```
   Tada nukopijuokite `.env.example` į `.env` ir atkomentuokite eilutes `DATABASE_URL` ir
   `TEST_DATABASE_URL`. Be `.env` programa naudoja SQLite failą `mokykla.db`.
3. Demonstraciniai duomenys (ištrina esamus duomenis ir schemą sukuria migracijomis):
   ```powershell
   python seed.py
   ```
4. Programa ir fono procesas – kiekvienas atskirame terminale:
   ```powershell
   python app.py
   python worker.py
   ```

Atidarykite http://127.0.0.1:5000. `python app.py` paleidžiant duomenų bazė atnaujinama iki naujausios
migracijos. Fono procesas kas minutę siunčia pranešimus iš eilės, kasdien 7 val. siunčia priminimus ir
žymi vėluojančias priemones, kiekvieno mėnesio 1 d. parengia mėnesio suvestinę.

## Demonstraciniai naudotojai

| Rolė | El. paštas | Slaptažodis |
|------|-----------|-------------|
| Administratorius | admin@mokykla.lt | admin123 |
| Mokytoja, komisijos pirmininkė | ona@mokykla.lt | mokytojas123 |
| Mokytojas, komisijos sekretorius | tomas@mokykla.lt | mokytojas123 |
| Mokytojas | jonas@mokykla.lt | mokytojas123 |
| Tėvas | tevas@demo.lt | tevas123 |

Demonstraciniuose duomenyse yra trys Vaiko gerovės komisijos atvejai: įvykęs posėdis su
priemonėmis ir protokolu, suplanuotas posėdis ir naujas kreipimasis.

## Testai

```powershell
pytest                                # visi testai (PostgreSQL testai – jei nurodytas TEST_DATABASE_URL)
pytest -m "not postgres"              # tik SQLite testai
pytest -m postgres                    # lygiagretaus siuntimo ir numeravimo testai PostgreSQL
pytest --cov=services --cov=routes --cov-report=term-missing
python scripts\nfr_matavimai.py       # nefunkcinių reikalavimų matavimai
```

## Migracijos

```powershell
flask --app app atnaujinti-db         # atnaujina schemą iki naujausios versijos
flask --app app db current            # dabartinė schemos versija
```

## Saugumas

- Vaiko gerovės komisijos duomenis mato tik komisijos nariai ir administratorius, kitiems grąžinamas
  atsakymas „Nerasta“; peržiūros ir pakeitimai registruojami veiklos žurnale
- Visose formose CSRF žetonas; slaptažodžiai saugomi maišos pavidalu; dviejų veiksnių autentikacija;
  prisijungimo bandymų ribojimas
- Pranešimų šablonai vykdomi smėliadėžėje ir gauna tik leistinus laukus; komisijos el. laiškuose nėra
  svarstymo esmės, tik nuoroda į sistemą
- Dokumentai saugomi už viešo katalogo ribų, atsisiunčiami tik turint teisę; tikrinama SHA-256 suma
- Importuojami failai tikrinami pagal dydį, plėtinį ir turinį; formulės nevykdomos, eksportuojant
  ataskaitą CSV formulių pradžios simboliai neutralizuojami
