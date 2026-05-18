# Mokyklos valdymo platforma

Modernios web platformos prototipas mokyklai. Skirtas mokytojams ir administracijai valdyti klases, mokinius ir diplomus iš seminarų.

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

### 1. Aktyvuoti virtualią aplinką

**Windows (PowerShell):**
```powershell
cd C:\Users\astij\mokyklos-platforma
.\venv\Scripts\Activate.ps1
```

### 2. Užpildyti duomenų bazę demo duomenimis (vieną kartą)

```powershell
python seed.py
```

### 3. Paleisti serverį

```powershell
python app.py
```

Atidarykite naršyklėje: **http://127.0.0.1:5000**

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
