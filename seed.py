"""Pradėtinių duomenų užpildymo skriptas.

Paleidžia: python seed.py
Sukuria demo vartotojus, klases, mokinius ir skelbimus.
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
from models import db, User, Klase, Mokinys, Skelbimas


def uzpildyti_db(naudoti_esama_app=False):
    """Užpildo duomenų bazę demo duomenimis."""
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
            vardas="ADMIN",
            pavarde="",
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

        # Duomenys formatu: (vardas, pavardė, gim. data, email, tel, adresas,
        #                    motinos_vardas, motinos_tel, motinos_email,
        #                    tėvo_vardas, tėvo_tel, tėvo_email,
        #                    autobusas, gerovės_kom, geroves_data, geroves_pastabos)

        mokiniai_5a = [
            ("Aistė", "Adomaitytė", date(2014, 3, 15), "aiste.a@mokinys.lt", "+370 600 11111", "Noriūnų k., Kupiškio r.",
             "Jurgita Adomaitienė", "+370 612 11111", "jurgita.a@email.lt",
             "Rimantas Adomaitis", "+370 612 11112", "rimantas.a@email.lt",
             True, False, None, None),

            ("Domas", "Butkus", date(2014, 5, 22), None, "+370 600 22222", "Mokyklos g. 5, Noriūnai, Kupiškio r.",
             "Inga Butkienė", "+370 612 22222", "inga.b@email.lt",
             "Mindaugas Butkus", "+370 612 22223", None,
             True, True, date(2025, 10, 15), "Aptarta mokinio adaptacijos eiga, sustiprintas individualus darbas su klasės vadovu."),

            ("Eglė", "Čepaitė", date(2014, 1, 10), "egle.c@mokinys.lt", None, "Adomynės k., Kupiškio r.",
             "Vilma Čepienė", "+370 612 33333", "vilma.c@email.lt",
             None, None, None,
             False, False, None, None),

            ("Gabrielius", "Dapkus", date(2014, 7, 8), None, "+370 600 44444", "Šimonių k., Kupiškio r.",
             "Daiva Dapkienė", "+370 612 44444", "daiva.d@email.lt",
             "Tomas Dapkus", "+370 612 44445", "tomas.d@email.lt",
             True, False, None, None),

            ("Ieva", "Eidukaitė", date(2014, 9, 30), "ieva.e@mokinys.lt", "+370 600 55555", "Vilniaus g. 8, Kupiškis",
             "Asta Eidukienė", "+370 612 55555", "asta.e@email.lt",
             "Vytautas Eidukas", "+370 612 55556", None,
             False, False, None, None),
        ]

        mokiniai_8b = [
            ("Justas", "Gricius", date(2011, 2, 14), "justas.g@mokinys.lt", "+370 600 66666", "Vytauto g. 12, Kupiškis",
             "Lina Gricienė", "+370 612 66666", "lina.g@email.lt",
             "Arūnas Gricius", "+370 612 66667", "arunas.g@email.lt",
             False, True, date(2025, 9, 20), "Mokymosi sunkumai matematikos pamokose, rekomenduotas papildomas mokytojo konsultavimas."),

            ("Kamilė", "Jasiūnaitė", date(2011, 4, 18), None, "+370 600 77777", "Subačiaus k., Kupiškio r.",
             "Rita Jasiūnienė", "+370 612 77777", "rita.j@email.lt",
             "Donatas Jasiūnas", "+370 612 77778", None,
             True, False, None, None),

            ("Lukas", "Karpavičius", date(2011, 6, 25), "lukas.k@mokinys.lt", None, "Salamiesčio k., Kupiškio r.",
             "Aurelija Karpavičienė", "+370 612 88888", "aurelija.k@email.lt",
             "Marius Karpavičius", "+370 612 88889", "marius.k@email.lt",
             False, False, None, None),

            ("Milda", "Liutkutė", date(2011, 8, 3), None, "+370 600 88888", "Gedimino g. 22, Kupiškis",
             "Gintarė Liutkienė", "+370 612 99999", "gintare.l@email.lt",
             None, None, None,
             False, False, None, None),
        ]

        mokiniai_10a = [
            ("Nojus", "Marčiulionis", date(2009, 10, 11), "nojus.m@mokinys.lt", "+370 600 99999", "Skapiškio k., Kupiškio r.",
             "Sandra Marčiulionienė", "+370 613 11111", "sandra.m@email.lt",
             "Arvydas Marčiulionis", "+370 613 11112", "arvydas.m@email.lt",
             False, False, None, None),

            ("Olga", "Norvilaitė", date(2009, 12, 27), None, "+370 600 12121", "Antašavos k., Kupiškio r.",
             "Tatjana Norvilienė", "+370 613 22222", "tatjana.n@email.lt",
             "Pavel Norvila", "+370 613 22223", None,
             True, False, None, None),

            ("Paulius", "Petraitis", date(2009, 11, 5), "paulius.p@mokinys.lt", None, "Aušros g. 4, Kupiškis",
             "Rita Petraitienė", "+370 613 33333", "rita.p@email.lt",
             "Saulius Petraitis", "+370 613 33334", "saulius.p@email.lt",
             False, True, date(2025, 11, 5), "Drausminio pobūdžio incidentas. Susitarta dėl elgesio sutarties su mokiniu ir tėvais."),
        ]

        def _prideti_mokini(duomenys, klases_id):
            (vardas, pavarde, gdata, email, tel, adr,
             m_vardas, m_tel, m_email,
             t_vardas, t_tel, t_email,
             autobusas, gerov_kom, gerov_data, gerov_past) = duomenys

            m = Mokinys(
                vardas=vardas, pavarde=pavarde, gimimo_data=gdata,
                email=email, telefonas=tel, adresas=adr,
                motinos_vardas=m_vardas, motinos_telefonas=m_tel, motinos_email=m_email,
                tevo_vardas=t_vardas, tevo_telefonas=t_tel, tevo_email=t_email,
                mokyklos_autobusas=autobusas,
                geroves_komisija=gerov_kom,
                geroves_komisija_data=gerov_data,
                geroves_komisija_pastabos=gerov_past,
                klases_id=klases_id,
            )
            db.session.add(m)
            return m

        for d in mokiniai_5a:
            _prideti_mokini(d, klase_5a.id)
        for d in mokiniai_8b:
            _prideti_mokini(d, klase_8b.id)
        for d in mokiniai_10a:
            _prideti_mokini(d, klase_10a.id)

        db.session.commit()

        print("Kuriama demo tevo paskyra...")
        petras_tevas = User(
            vardas="Petras",
            pavarde="Demo",
            email="tevas@demo.lt",
            telefonas="+37060000000",
            role="tevas",
        )
        petras_tevas.nustatyti_slaptazodi("tevas123")
        # Priskirti pirmus 2 mokinius (Aiste ir Domas is 5A)
        pirmieji_du = Mokinys.query.limit(2).all()
        petras_tevas.vaikai = pirmieji_du
        db.session.add(petras_tevas)
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
                "pavadinimas": "Vaiko gerovės komisijos posėdis",
                "turinys": "Kitos savaitės antradienį, 15:00 vyks vaiko gerovės komisijos posėdis. Bus svarstomos kelios mokinių situacijos. Klasės vadovus prašome pateikti savo pastebėjimus iki pirmadienio.",
                "svarbus": True,
                "vartotojo_id": admin.id,
                "dienu_atgal": 2,
            },
            {
                "pavadinimas": "Atvirų durų diena - lapkričio 25 d.",
                "turinys": "Mieli tėvai, kviečiame į atvirų durų dieną lapkričio 25 d. 16:00-19:00. Galėsite susipažinti su mokyklos veikla, pabendrauti su klasių vadovais bei mokytojais.",
                "svarbus": False,
                "matomas_tevams": True,
                "vartotojo_id": admin.id,
                "dienu_atgal": 3,
            },
            {
                "pavadinimas": "Kalėdinis koncertas",
                "turinys": "Gruodžio 18 d. 18:00 mokyklos salėje vyks kalėdinis koncertas. Pasirodys mūsų talentingi mokiniai - choras, šokio grupė ir teatro studija. Laukiame ir tėvų!",
                "svarbus": False,
                "matomas_tevams": True,
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
              f"{Skelbimas.query.count()} skelbimai\n")


if __name__ == "__main__":
    uzpildyti_db()
