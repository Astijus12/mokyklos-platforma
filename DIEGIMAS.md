# 🚀 Kaip iškelti sistemą į produkciją

Šis vadovas nurodo, kaip atnaujinti dabar veikiančią sistemą su visais naujais
uždaviniais (tėvų portalas, 2FA, REST API, testai).

## 🎯 Du keliai

**Kelias A: Render.com** — atnaujinti jau egzistuojantį deploy'mentą (**paprastas, rekomenduojamas**).
**Kelias B: Docker** — visiškai naujas produkcinis diegimas ant nuosavo serverio.

---

# 📗 KELIAS A: Render.com atnaujinimas

## 1️⃣ Patikrinti, kad testai veikia lokaliai

```bash
cd C:\Users\astij\mokyklos-platforma
.\venv\Scripts\python.exe -m pytest
```

Turi būti: **`60 passed`** ✅

## 2️⃣ Užcommitint pakeitimus į git

```bash
cd C:\Users\astij\mokyklos-platforma
git add -A
git status
```

Peržiūrėk sąrašą. Jei viskas atrodo gerai:

```bash
git commit -m "Baigiamoji praktika: tevu portalas + 2FA + REST API + testai + Docker"
```

## 3️⃣ Pastumti į GitHub

```bash
git push origin main
```

## 4️⃣ Palaukti Render deploy'o (~3-5 minutės)

Render automatiškai:
1. Pamato push'ą į GitHub
2. Įdiegia naujas priklausomybes (`pyotp`, `qrcode`, `psycopg2-binary`)
3. Paleidžia `gunicorn wsgi:app`
4. `wsgi.py` **automatiškai atlieka migracijas** (prideda naujus DB laukus)

Sekti procesą: https://dashboard.render.com → tavo servisas → Logs

## 5️⃣ Patikrinti, kad veikia

Atsidaryk deploy'nto sistemos URL. Naujos funkcijos:

| Testas | Kur patikrinti |
|--------|----------------|
| Tėvų prisijungimas | Login puslapyje matysi Tėvo demo kredencialus |
| Tėvų portalas | Prisijungęs kaip tėvas — matysi `/tevams/` |
| 2FA | Profilio puslapyje → mygtukas **2FA** |
| REST API | https://tavo-url.onrender.com/api/v1/health |
| Skelbimų matomumas | Kuriant skelbimą — nauja checkbox „Matomas tėvams" |

## ⚠️ Svarbu apie Render Free Tier

- **SQLite DB dingsta** po serverio užmigimo (15 min neaktyvumo)
- Demo duomenys atkuriami automatiškai kiekvienu paleidimu
- Realiam naudojimui — reikėtų persistentinės DB (žr. **Kelias B**)

---

# 📘 KELIAS B: Docker produkcinis diegimas

Naudoti, kai reikia stabilaus produkcijos servisos su išliekančia DB.

## 📋 Prieš pradedant

Nuosavame serveryje (Ubuntu / Debian / Windows Server / Mac) turi būti įdiegta:

- **Docker Engine 20.10+** — [docs.docker.com/engine/install](https://docs.docker.com/engine/install/)
- **Docker Compose 2.0+** — įeina į Docker Desktop
- Bent **1 GB RAM** ir **2 GB disko**

## 1️⃣ Klonuoti kodą

```bash
git clone https://github.com/Astijus12/mokyklos-platforma.git
cd mokyklos-platforma
```

## 2️⃣ Paruošti aplinkos kintamuosius

```bash
cp .env.example .env
```

Sugeneruoti saugius slaptažodžius:

```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(24))"
```

Įrašyk rezultatus į `.env` failą.

## 3️⃣ Paleisti visus servisus

```bash
docker-compose up -d --build
```

Bus paleisti **3 konteineriai**:
- `mokykla_web` — Flask + Gunicorn (portas 8000)
- `mokykla_db` — PostgreSQL 16
- `mokykla_backup` — kasdien atlieka DB atsargines kopijas

## 4️⃣ Patikrinti būseną

```bash
docker-compose ps
docker-compose logs -f web
```

Kai matysi `Booting worker with pid: ...` — sistema veikia!

## 5️⃣ Atidaryti naršyklėje

http://localhost:8000

## 6️⃣ Papildomai — priedėti HTTPS (produkcijai)

Rekomenduoju naudoti **Caddy** reverse-proxy — jis automatiškai gauna Let's Encrypt sertifikatus:

```bash
# Sukurti Caddyfile
cat > Caddyfile <<EOF
mokykla.tavo-domenas.lt {
    reverse_proxy web:8000
}
EOF
```

Ir pridėti Caddy į `docker-compose.yml` kaip 4-tą servisą.

---

# 🔒 Saugumo checklist prieš atidarant realiems vartotojams

- [ ] Pakeistas `SECRET_KEY` į stiprų atsitiktinį (>=32 simboliai)
- [ ] Pakeistas `DB_PASSWORD` (jei Docker)
- [ ] Pakeisti demo admin@mokykla.lt slaptažodžiai
- [ ] Įjungta **HTTPS** (Let's Encrypt / Caddy / nginx)
- [ ] Įjungta **2FA** administratoriams
- [ ] Sukonfigūruotos atsarginės kopijos
- [ ] Ištrinti demo vartotojai (jei nenaudojami)
- [ ] Ištrinti `.env` iš git (jau yra `.gitignore`)

---

# 📱 Pirmoji tėvo paskyra

Kai sistema veikia produkcijoje, sukurk pirmojo tėvo paskyrą:

1. Prisijunk kaip administratorius
2. Meniu → **Vartotojai** → **Naujas vartotojas**
3. Įvesk tėvo duomenis, rolė = **Tėvas / Globėjas**
4. Grįžk į vartotojų sąrašą → paspausk **👥** ikoną prie tėvo
5. Pažymėk jo vaikus → **Išsaugoti**
6. Duok tėvui prisijungimo kredencialus

## Perduoti tėvams instrukcijas

Rekomenduoju parengti trumpą PDF instrukciją tėvams su:
- URL, kur prisijungti
- Kaip pakeisti slaptažodį
- Kaip įjungti 2FA
- Ką jie ras portale

---

# ❓ Problemų sprendimas

**Render:** deploy'as nepavyksta?
→ Patikrink logs Render dashboarde. Dažniausia klaida — `psycopg2-binary` diegimas. Sprendimas — patikrinti `runtime.txt` (turi būti Python 3.12+).

**Render:** naujos funkcijos nesirodo?
→ Palauk 5 min ir refresh. Jei vis vien - clear browser cache.

**Docker:** `port already in use`?
→ Kažkas jau užima 8000. Sustabdyk arba pakeisk portą `docker-compose.yml`.

**Docker:** `database connection refused`?
→ PG dar startuoja. Palauk 10 sek., healthcheck išspręs automatiškai.
