# 🚀 Paskelbimo (Deploy) instrukcija - Render.com

Šis vadovas paaiškina, kaip paskelbti mokyklos platformą internete naudojant nemokamą Render.com paslaugą.

## 📋 Žingsniai

### 1️⃣ Sukurkite GitHub paskyrą (jei dar neturite)

1. Eikite į https://github.com/signup
2. Užsiregistruokite (galite naudoti savo el. paštą)
3. Patvirtinkite el. paštą

### 2️⃣ Sukurkite naują GitHub repozitoriją

1. Prisijungę paspauskite **"+"** mygtuką viršuje, dešinėje → **"New repository"**
2. **Repository name:** `mokyklos-platforma`
3. **Description:** "Mokyklos valdymo platforma - praktikos projektas"
4. Pasirinkite **Public** (kad Render galėtų pasiekti)
5. **NESPAUSKITE** "Add a README file" - mes jau turime
6. **NESPAUSKITE** "Add .gitignore" - jau turime
7. Paspauskite **"Create repository"**

### 3️⃣ Įkelkite kodą į GitHub

Atsidaro puslapis su instrukcijomis. Atlikite šitą PowerShell terminale (savo kompiuteryje):

```powershell
cd C:\Users\astij\mokyklos-platforma

# Pakeiskite TAVO_VARDAS į savo GitHub vartotojo vardą:
git remote add origin https://github.com/TAVO_VARDAS/mokyklos-platforma.git
git branch -M main
git push -u origin main
```

⚠️ **Pirmą kartą** push'inant GitHub paprašys prisijungimo. Naudokite:
- **Username:** jūsų GitHub vardas
- **Password:** **Personal Access Token** (NE jūsų slaptažodis!)

Tokeną gausite čia: https://github.com/settings/tokens
- Spauskite "Generate new token (classic)"
- Pažymėkite "repo" pilną prieigą
- Sugeneruokite ir nukopijuokite tokeną
- Įklijuokite vietoj slaptažodžio

### 4️⃣ Sukurkite Render.com paskyrą

1. Eikite į https://render.com
2. Paspauskite **"Get Started"** arba **"Sign Up"**
3. **Pasirinkite "Sign up with GitHub"** - tai svarbu! Tai sujungs jūsų paskyras
4. Patvirtinkite prieigą savo GitHub repozitorijoms

### 5️⃣ Sukurkite Web Service Renderyje

1. Prisijungę paspauskite **"+ New"** → **"Web Service"**
2. Pasirinkite **"Build and deploy from a Git repository"** → **"Next"**
3. Sąraše rasite savo `mokyklos-platforma` repozitoriją → spauskite **"Connect"**

Render automatiškai aptiks `render.yaml` failą ir užpildys nustatymus. Patikrinkite:

| Laukas | Reikšmė |
|--------|---------|
| **Name** | `mokyklos-platforma` (gali keisti) |
| **Region** | Frankfurt (arčiausiai Lietuvos) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn wsgi:app` |
| **Plan** | **Free** |

4. Paspauskite **"Create Web Service"**

### 6️⃣ Laukite kol bus diegiama

Render automatiškai:
- Klonuoja jūsų kodą iš GitHub
- Įdiegia Python paketus
- Paleidžia serverį
- Sukuria duomenų bazę su demo duomenimis

Tai užtruks **5-10 minučių pirmą kartą**.

Kai pamatysi `"Your service is live"` - viskas paruošta! ✅

### 7️⃣ Atidarykite svetainę

Render duos jums URL formato:
```
https://mokyklos-platforma.onrender.com
```
(arba panašų - su atsitiktiniu sufiksu)

Atidarykite tą URL naršyklėje. Prisijunkite su demo paskyra:
- **Email:** admin@mokykla.lt
- **Slaptažodis:** admin123

## 🎉 Pasidalinimas

Dalinkitės URL su bet kuo! Tinka:
- WhatsApp/Messenger žinutei
- El. laiškui
- Per Teams/Zoom ekrano demonstracijai

## ⚠️ Svarbu žinoti apie nemokamą Render planą

- **Pirmas atsidarymas po 15 min neaktyvumo** užtrunka ~30 sek (vadinama "cold start"). Tai normalu.
- **Failai (diplomai) gali pasimesti** po serverio restarto - demo režimas.
- **Duomenų bazė** kiekvieną restartą atsistato į pradines reikšmes (demo duomenis).

Realiam naudojimui galima:
- Užsisakyti Render mokamą planą ($7/mėn) su persistentine duomenų baze
- Arba pakeisti SQLite į PostgreSQL (Render duoda nemokamą)

## 🔄 Atnaujinimas

Pakeitėte kodą? Tiesiog:

```powershell
cd C:\Users\astij\mokyklos-platforma
git add .
git commit -m "Atnaujinimas"
git push
```

Render automatiškai atpažins push'ą ir iš naujo diegs jūsų svetainę. ✨

## 🆘 Problemos?

**"Build failed"** Render logs:
- Patikrinkite, ar visi failai įkelti į GitHub
- Patikrinkite, ar `requirements.txt` yra teisingas

**"Application failed to respond"**:
- Patikrinkite Render logs (skiltis "Logs" Render dashboard'e)
- Dažniausia priežastis - klaida `wsgi.py` faile arba paketų nesuderinamumas

**Push nepriima slaptažodžio**:
- GitHub jau seniai nepriima slaptažodžių per HTTPS
- Naudokite Personal Access Token (žiūr. instrukciją aukščiau)
