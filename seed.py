"""Pradėtinių duomenų užpildymo skriptas.

Paleidžia: python seed.py
Sukuria demo vartotojus, klases, mokinius, pažymius ir skelbimus.
"""
import sys
import random
from datetime import date, datetime, timedelta

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import create_app
from models import db, User, Klase, Mokinys, Skelbimas, Pazymys, DALYKAI


def uzpildyti_db(naudoti_esama_app=False):
    """Užpildo duomenų bazę demo duomenimis.

    Args:
        naudoti_esama_app: jei True, naudoja jau veikiančią aplikacijos kontekstą
                          (tai naudojama deploying serverio kontekste).
    """
    if naudoti_esama_app:
        _uzpildyti()
    else:
        app = create_app()
        with app.app_context():
            _uzpildyti()


def _uzpildyti():
        print("Valoma duomenų bazė...")
        db.drop_all()
        db.create_all()

        print("Kuriami vartotojai...")
        admin = User(
            vardas="Rasa",
            pavarde="Petraitienė",
            email="admin@mokykla.lt",
            role="administratorius",
        )
        admin.nustatyti_slaptazodi("admin123")

        jonas = User(
            vardas="Jonas",
            pavarde="Jonaitis",
            email="jonas@mokykla.lt",
            role="mokytojas",
        )
        jonas.nustatyti_slaptazodi("mokytojas123")

        ona = User(
            vardas="Ona",
            pavarde="Kazlauskienė",
            email="ona@mokykla.lt",
            role="mokytojas",
        )
        ona.nustatyti_slaptazodi("mokytojas123")

        tomas = User(
            vardas="Tomas",
            pavarde="Vaitkus",
            email="tomas@mokykla.lt",
            role="mokytojas",
        )
        tomas.nustatyti_slaptazodi("mokytojas123")

        db.session.add_all([admin, jonas, ona, tomas])
        db.session.commit()

        print("Kuriamos klasės...")
        klase_5a = Klase(pavadinimas="5A", mokslo_metai="2025-2026", vadovo_id=jonas.id)
        klase_8b = Klase(pavadinimas="8B", mokslo_metai="2025-2026", vadovo_id=ona.id)
        klase_10a = Klase(pavadinimas="10A", mokslo_metai="2025-2026", vadovo_id=tomas.id)
        klase_2g = Klase(pavadinimas="IIG", mokslo_metai="2025-2026")

        db.session.add_all([klase_5a, klase_8b, klase_10a, klase_2g])
        db.session.commit()

        print("Kuriami mokiniai...")
        mokiniai_5a = [
            ("Aistė", "Adomaitytė", date(2014, 3, 15), "aiste.a@mokinys.lt", "+370 600 11111", "Vilniaus g. 15, Vilnius"),
            ("Domas", "Butkus", date(2014, 5, 22), None, "+370 600 22222", "Gedimino pr. 5, Vilnius"),
            ("Eglė", "Čepaitė", date(2014, 1, 10), "egle.c@mokinys.lt", None, "Žirmūnų g. 24, Vilnius"),
            ("Gabrielius", "Dapkus", date(2014, 7, 8), None, "+370 600 44444", "Žemaitės g. 7, Vilnius"),
            ("Ieva", "Eidukaitė", date(2014, 9, 30), "ieva.e@mokinys.lt", "+370 600 55555", "Antakalnio g. 32, Vilnius"),
        ]
        mokiniai_8b = [
            ("Justas", "Gricius", date(2011, 2, 14), "justas.g@mokinys.lt", "+370 600 66666", "Vingio g. 11, Vilnius"),
            ("Kamilė", "Jasiūnaitė", date(2011, 4, 18), None, "+370 600 77777", "Žalgirio g. 90, Vilnius"),
            ("Lukas", "Karpavičius", date(2011, 6, 25), "lukas.k@mokinys.lt", None, "Saltoniškių g. 8, Vilnius"),
            ("Milda", "Liutkutė", date(2011, 8, 3), None, "+370 600 88888", "Kauno g. 14, Vilnius"),
        ]
        mokiniai_10a = [
            ("Nojus", "Marčiulionis", date(2009, 10, 11), "nojus.m@mokinys.lt", "+370 600 99999", "Konstitucijos pr. 21, Vilnius"),
            ("Olga", "Norvilaitė", date(2009, 12, 27), None, "+370 600 12121", "Pylimo g. 33, Vilnius"),
            ("Paulius", "Petraitis", date(2009, 11, 5), "paulius.p@mokinys.lt", None, "Vokiečių g. 9, Vilnius"),
        ]

        visi_mokiniai = []

        for vardas, pavarde, gdata, email, tel, adr in mokiniai_5a:
            m = Mokinys(
                vardas=vardas, pavarde=pavarde, gimimo_data=gdata,
                email=email, telefonas=tel, adresas=adr,
                klases_id=klase_5a.id,
            )
            db.session.add(m)
            visi_mokiniai.append(m)

        for vardas, pavarde, gdata, email, tel, adr in mokiniai_8b:
            m = Mokinys(
                vardas=vardas, pavarde=pavarde, gimimo_data=gdata,
                email=email, telefonas=tel, adresas=adr,
                klases_id=klase_8b.id,
            )
            db.session.add(m)
            visi_mokiniai.append(m)

        for vardas, pavarde, gdata, email, tel, adr in mokiniai_10a:
            m = Mokinys(
                vardas=vardas, pavarde=pavarde, gimimo_data=gdata,
                email=email, telefonas=tel, adresas=adr,
                klases_id=klase_10a.id,
            )
            db.session.add(m)
            visi_mokiniai.append(m)

        db.session.commit()

        print("Kuriami pažymiai...")
        mokytojai = [jonas, ona, tomas]
        komentarai_geri = [
            "Kontrolinis darbas", "Aktyvumas pamokoje", "Atsakymas raštu",
            "Savarankiškas darbas", "Klausimynas", "Projektas",
        ]
        komentarai_blogi = [
            "Nepateikė namų darbų", "Trūksta pasiruošimo", "Neaktyvus pamokoje",
        ]

        random.seed(42)
        for mokinys in visi_mokiniai:
            pasirinkti_dalykai = random.sample(DALYKAI, k=random.randint(4, 7))
            for dalykas in pasirinkti_dalykai:
                for _ in range(random.randint(1, 4)):
                    if random.random() < 0.7:
                        pazymys_reiksme = random.randint(7, 10)
                        komentaras = random.choice(komentarai_geri)
                    else:
                        pazymys_reiksme = random.randint(3, 6)
                        komentaras = random.choice(komentarai_blogi)

                    dienu_atgal = random.randint(1, 60)
                    pazymio_data = date.today() - timedelta(days=dienu_atgal)

                    p = Pazymys(
                        mokinio_id=mokinys.id,
                        mokytojo_id=random.choice(mokytojai).id,
                        dalykas=dalykas,
                        pazymys=pazymys_reiksme,
                        komentaras=komentaras,
                        data=pazymio_data,
                    )
                    db.session.add(p)

        db.session.commit()

        print("Kuriami skelbimai...")
        skelbimai_data = [
            {
                "pavadinimas": "Mokytojų taryba penktadienį 14:00",
                "turinys": "Primename, kad penktadienį, 14:00 mokytojų kambaryje vyks mokytojų tarybos posėdis. Aptarsime II ketvirčio rezultatus, planuojame kalėdinius renginius. Dalyvavimas privalomas visiems pedagoginiams darbuotojams.",
                "svarbus": True,
                "vartotojo_id": admin.id,
                "dienu_atgal": 1,
            },
            {
                "pavadinimas": "Atvirų durų diena - lapkričio 25 d.",
                "turinys": "Mokykloje organizuojama Atvirų durų diena tėvams. Renginys vyks 16:00-19:00. Kviečiame mokytojus pasiruošti savo dalykų pristatymus ir prisidėti prie šios svarbios mokyklos bendruomenės akimirkos.",
                "svarbus": False,
                "vartotojo_id": admin.id,
                "dienu_atgal": 3,
            },
            {
                "pavadinimas": "Kalėdinis koncertas",
                "turinys": "Gruodžio 18 d. 18:00 mokyklos salėje vyks kalėdinis koncertas. Pasirodys mūsų talentingi mokiniai - choras, šokio grupė ir teatro studija. Laukiame visų darbuotojų!",
                "svarbus": False,
                "vartotojo_id": ona.id,
                "dienu_atgal": 5,
            },
            {
                "pavadinimas": "Skaitmeninio raštingumo seminaras",
                "turinys": "Lapkričio 12 d. organizuojamas nuotolinis seminaras 'Skaitmeninių įrankių integracija pamokose'. Registracija iki lapkričio 10 d. Dalyvavusiems mokytojams bus išduoti pažymėjimai.",
                "svarbus": False,
                "vartotojo_id": jonas.id,
                "dienu_atgal": 7,
            },
            {
                "pavadinimas": "Mokinių pažangos vertinimas",
                "turinys": "Primename, kad mokinių pažangos vertinimo ataskaitos turi būti pateiktos iki mėnesio pabaigos. Naudokitės nauja sistema pažymių įrašymui.",
                "svarbus": True,
                "vartotojo_id": admin.id,
                "dienu_atgal": 10,
            },
        ]

        for sd in skelbimai_data:
            dienu_atgal = sd.pop("dienu_atgal")
            s = Skelbimas(**sd)
            s.sukurtas = datetime.now() - timedelta(days=dienu_atgal)
            db.session.add(s)

        db.session.commit()

        print("\n" + "="*50)
        print("✓ DEMO DUOMENYS SĖKMINGAI SUKURTI!")
        print("="*50)
        print("\nPrisijungimo duomenys:\n")
        print("  ADMINISTRATORIUS:")
        print("    El. paštas: admin@mokykla.lt")
        print("    Slaptažodis: admin123\n")
        print("  MOKYTOJAI:")
        print("    jonas@mokykla.lt / mokytojas123")
        print("    ona@mokykla.lt / mokytojas123")
        print("    tomas@mokykla.lt / mokytojas123\n")
        print(f"Sukurta: {User.query.count()} vartotojai, "
              f"{Klase.query.count()} klasės, "
              f"{Mokinys.query.count()} mokiniai, "
              f"{Pazymys.query.count()} pažymiai, "
              f"{Skelbimas.query.count()} skelbimai\n")


if __name__ == "__main__":
    uzpildyti_db()
