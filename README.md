# Noriūnų Jono Černiaus mokyklos sistema

Modernios web platformos prototipas Noriūnų Jono Černiaus mokyklai. Skirtas mokytojams ir administracijai valdyti klases, mokinius ir diplomus iš seminarų.

## Technologijos

- **Backend:** Python 3.13 + Flask
- **Duomenų bazė:** SQLite + SQLAlchemy
- **Frontend:** HTML + Tailwind CSS + JavaScript
- **Autentikacija:** Flask-Login (su slaptažodžių šifravimu)

## Funkcionalumas

| Sekcija | Aprašymas | Kas gali naudoti |
|---------|-----------|------------------|
| Prisijungimas | Saugus prisijungimas su slaptažodžiu | Visi |
| Pradžia (Dashboard) | Statistika ir greita prieiga | Visi |
| Klasės | Klasių sąrašas, kūrimas, redagavimas | Mokytojai (žiūri), Admin (valdo) |
| Mokiniai | Mokinių valdymas, paieška, filtravimas | Visi mokytojai |
| Diplomai | Diplomų įkėlimas (PDF, JPG, PNG) | Visi mokytojai |
| Vartotojai | Mokytojų ir administratorių valdymas | Tik administratorius |

## Paleidimas

### 1. Aktyvuoti virtualią aplinką ir įdiegti paketus

**Windows (PowerShell):**
```powershell
cd C:\Users\astij\mokyklos-platforma
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Paruošti PostgreSQL (vieną kartą)

Kūrimui naudojamas vietinis PostgreSQL. Naudotoją `mokykla` ir duomenų bazes
`mokykla_db` (programai) bei `mokykla_test` (PostgreSQL testams) sukuria scenarijus:

```powershell
& "C:\Program Files\PostgreSQL\19\bin\psql.exe" -U postgres -f scripts\sukurti_duomenu_baze.sql
```

Tada nukopijuokite `.env.example` į `.env` ir atkomentuokite eilutes `DATABASE_URL`
ir `TEST_DATABASE_URL`. Be `.env` programa naudoja SQLite failą `mokykla.db`.

### 3. Užpildyti duomenų bazę demo duomenimis (vieną kartą)

```powershell
python seed.py
```

Scenarijus ištrina lenteles ir schemą sukuria migracijomis (`migrations/`).

### 4. Paleisti serverį ir fono procesą

```powershell
python app.py
python worker.py
```

`python app.py` paleidžiant atnaujina duomenų bazę iki naujausios migracijos.
Fono procesas (`worker.py`) vykdo planuoklės užduotis; jį paleiskite atskirame terminale.

Atidarykite naršyklėje: **http://127.0.0.1:5000**

### Migracijos ir testai

```powershell
flask --app app atnaujinti-db      # atnaujina schemą (tinka ir senai DB be migracijų)
flask --app app db current         # dabartinė schemos versija
pytest -m "not postgres"           # SQLite testai
pytest -m postgres                 # PostgreSQL testai (reikia TEST_DATABASE_URL)
```

### Docker

```powershell
docker compose up --build
```

Paleidžiami konteineriai `web` (programa), `worker` (fono procesas), `db` (PostgreSQL 16)
ir `backup` (atsarginės kopijos).

## Demo prisijungimai

**Administratorius:**
- El. paštas: `admin@mokykla.lt`
- Slaptažodis: `admin123`

**Mokytojai:**
- `jonas@mokykla.lt` / `mokytojas123`
- `ona@mokykla.lt` / `mokytojas123`
- `tomas@mokykla.lt` / `mokytojas123`

## Projekto struktūra

```
mokyklos-platforma/
├── app.py                  # Pagrindinis Flask failas
├── config.py               # Konfigūracija
├── models.py               # Duomenų bazės modeliai
├── seed.py                 # Demo duomenų užpildymas
├── requirements.txt        # Python paketai
├── routes/                 # URL keliai (route'ai)
│   ├── auth.py             # Prisijungimas
│   ├── dashboard.py        # Pagrindinis puslapis
│   ├── classes.py          # Klasės
│   ├── students.py         # Mokiniai
│   ├── diplomas.py         # Diplomai
│   └── users.py            # Vartotojai
├── templates/              # HTML šablonai (Jinja2)
│   ├── base.html           # Bazinis šablonas
│   ├── login.html
│   ├── dashboard.html
│   ├── classes/
│   ├── students/
│   ├── diplomas/
│   └── users/
├── static/
│   ├── css/style.css       # Stiliai
│   ├── js/main.js          # JavaScript
│   └── uploads/            # Įkelti failai
└── mokykla.db              # SQLite duomenų bazė
```

## Saugumo aspektai

- Slaptažodžiai šifruojami (Werkzeug hash)
- Sesijos su saugiu raktu
- CSRF apsauga per Flask
- Failų tipų patikrinimas įkėlimo metu
- Rolėmis paremta prieiga (administratorius / mokytojas)

## Tolimesnis vystymas

Galimos funkcijos plėtimui:
- Mokinių pažymių valdymas
- Tvarkaraščio sistema
- Pranešimų sistema tarp mokytojų
- Tėvų prisijungimas
- Eksportas į PDF / Excel
- El. pašto pranešimai
