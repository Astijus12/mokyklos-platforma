# 🐳 Docker + PostgreSQL diegimas

Šis dokumentas aprašo, kaip paleisti mokyklos platformą **produkciniam naudojimui**
su Docker konteineriais ir PostgreSQL duomenų baze.

## 📋 Prieš pradedant

Reikalinga:
- Docker Engine 20.10+
- Docker Compose 2.0+
- Bent 1 GB laisvos RAM
- Bent 2 GB laisvos disko vietos

## 🚀 Greitas paleidimas

```bash
# 1. Nukopijuokite aplinkos kintamųjų šabloną
cp .env.example .env

# 2. Sugeneruokite saugius slaptažodžius ir įrašykite į .env
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(24))"

# 3. Paleiskite visus servisus
docker-compose up -d --build

# 4. Patikrinkite būseną
docker-compose ps
docker-compose logs -f web
```

Aplikacija bus pasiekiama: **http://localhost:8000**

## 🧱 Architektūra

Trys konteineriai:

| Servisas | Konteineris | Aprašymas |
|----------|-------------|-----------|
| `web`    | mokykla_web    | Flask aplikacija su Gunicorn (2 workers) |
| `db`     | mokykla_db     | PostgreSQL 16 (alpine) |
| `backup` | mokykla_backup | Kasdien atlieka atsarginę kopiją (30 d.) |

Duomenys saugomi Docker volumes:
- `postgres_data` — DB duomenys (nedingsta perkraunant)
- `uploads` — įkelti diplomai / dokumentai
- `./duomenys/atsargines_kopijos/` — .sql.gz atsarginės kopijos

## 💾 Atsarginės kopijos

**Automatinis režimas** — `backup` konteineris kasdien 24:00 valandų intervalu:
- Sukuria `mokykla_db_YYYY-MM-DD_HH-MM-SS.sql.gz`
- Ištrina kopijas senesnes nei 30 dienų
- Saugo `./duomenys/atsargines_kopijos/`

**Rankinis režimas:**

```bash
docker exec mokykla_backup /usr/local/bin/backup.sh
```

**Atkūrimas:**

```bash
chmod +x scripts/restore.sh
./scripts/restore.sh duomenys/atsargines_kopijos/mokykla_db_2026-09-21_12-00-00.sql.gz
```

## 🔧 Priežiūra

**Peržiūrėti log'us:**
```bash
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f backup
```

**Perleisti tik web servisą (pvz., po kodo pakeitimo):**
```bash
docker-compose up -d --build web
```

**Sustabdyti visus servisus:**
```bash
docker-compose down
```

**Sustabdyti IR pašalinti duomenis** (dėmesio - viskas dings):
```bash
docker-compose down -v
```

**Prisijungti prie DB:**
```bash
docker exec -it mokykla_db psql -U mokykla -d mokykla_db
```

## 🔒 Saugumo pastabos

Produkcijoje būtina:

1. **Pakeisti `SECRET_KEY`** ir `DB_PASSWORD` į stiprius, atsitiktinius
2. **Neatidaryti DB porto 5432** iš viešojo tinklo (jau nurodyta `127.0.0.1:5432`)
3. **Naudoti HTTPS** — pridėkite nginx / Caddy prieš `web` servisą
4. **Reguliariai atsinaujinti** Docker image'us:
   ```bash
   docker-compose pull && docker-compose up -d
   ```
5. **Stebėti atsarginių kopijų dydį** ir periodiškai perkelti į išorinį saugojimą

## 🧪 Testų paleidimas

Testai vyksta atskirai (be Docker), naudojant in-memory SQLite:

```bash
./venv/Scripts/python.exe -m pytest --cov=. --cov-report=term
```

## ❓ Problemų sprendimas

**"port is already allocated"** — kažkas jau naudoja 8000 arba 5432:
```bash
docker-compose down
# arba pakeiskite portus docker-compose.yml
```

**"database system is starting up"** — palaukite ~10 sek., healthcheck išspręs.

**Web konteineris crash'ina** — patikrinkite logs:
```bash
docker-compose logs web
```

Dažniausia priežastis: neteisingas `DATABASE_URL` arba `SECRET_KEY` .env faile.
