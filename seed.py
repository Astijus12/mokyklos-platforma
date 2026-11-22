"""Demonstracinių duomenų užpildymo scenarijus.

Paleidžia: python seed.py
Sukuria demonstracinius duomenis visiems moduliams: naudotojus, klases, mokinius,
skelbimus su renginiais kalendoriuje, renginius, diplomus (seminarų pažymėjimus),
Vaiko gerovės komisijos atvejus ir posėdžius, pažymų prašymus, importo pavyzdį,
ataskaitą ir išsiųstus pranešimus. Datos skaičiuojamos nuo šiandienos, todėl
demonstracija visada atrodo aktuali.

Duomenys kuriami per tas pačias paslaugas (services/), kurias naudoja programa,
todėl atsiranda ir pranešimai, PDF dokumentai su numeriais bei įrašai eilėje.
"""
import os
import sys
from datetime import date, datetime, time, timedelta

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import current_app
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from app import create_app
from db_atnaujinimas import sukurti_schema_is_naujo
from models import (db, User, Klase, Mokinys, Skelbimas, Renginys, Diplomas, EilesIrasas, VeiklosZurnalas,
                    VgkAtvejis, VgkPosedis, VgkSvarstymas, VgkDalyvis, VgkPriemone, utc_dabar)
from services.dokumentai import SRIFTAS, SRIFTAS_PARYSKINTAS, ProtokoloGeneratorius, _uzregistruoti_sriftus
from services.importas import ImportoVykdytojas
from services.ivykiai import skelbti
from services.kalendorius import prideti_darbo_dienas
from services.kanalai import ElPastoKanalas, SistemosKanalas
from services.pazymos import atmesti_prasyma, parengti_ataskaita, pateikti_prasyma, patvirtinti_prasyma
from services.priminimai import PriminimuKurejas
from services.siuntejas import PranesimuSiuntejas
from services.skelbimai import susieti_su_kalendoriumi
from services.vgk import issaugoti_posedi, pateikti_kreipimasi

MENESIAI_KILMININKU = ("sausio", "vasario", "kovo", "balandžio", "gegužės", "birželio", "liepos",
                       "rugpjūčio", "rugsėjo", "spalio", "lapkričio", "gruodžio")


def ar_demo_svetaine(aplinka=None):
    """Ar tai demonstracinė svetainė, kurios duomenys kuriami iš naujo kiekvieną kartą paleidžiant.

    Render nemokamame plane failai (PDF dokumentai, diplomai) po kiekvieno paleidimo
    dingsta, o duomenų bazė išlieka. Kad jie visada sutaptų, Render'yje (RENDER=true)
    duomenų bazė kuriama iš naujo kartu su failais. Kintamuoju DEMO_SVETAINE (1 arba 0)
    tai galima nurodyti tiesiogiai, pvz., DEMO_SVETAINE=0 – duomenys išsaugomi.
    """
    aplinka = os.environ if aplinka is None else aplinka
    nurodyta = aplinka.get("DEMO_SVETAINE")
    if nurodyta in ("0", "1"):
        return nurodyta == "1"
    return aplinka.get("RENDER") == "true"


def data_tekstu(diena):
    """2026-12-18 -> „gruodžio 18 d.“"""
    return f"{MENESIAI_KILMININKU[diena.month - 1]} {diena.day} d."


def mokslo_metai(siandien):
    pradzia = siandien.year if siandien.month >= 9 else siandien.year - 1
    return f"{pradzia}-{pradzia + 1}"


def uzpildyti_db(naudoti_esama_app=False, isvalyti=True):
    """Užpildo duomenų bazę demo duomenimis.

    isvalyti=True – prieš tai ištrinamos visos lentelės ir schema sukuriama
    migracijomis iš naujo; False – naudojama jau paruošta tuščia schema.
    """
    if naudoti_esama_app:
        _uzpildyti(isvalyti)
    else:
        app = create_app()
        with app.app_context():
            _uzpildyti(isvalyti)


def _naudotojas(vardas, pavarde, email, role, slaptazodis, **papildomai):
    naudotojas = User(vardas=vardas, pavarde=pavarde, email=email, role=role, **papildomai)
    naudotojas.nustatyti_slaptazodi(slaptazodis)
    db.session.add(naudotojas)
    return naudotojas


def _uzpildyti(isvalyti=True):
    if isvalyti:
        print("Valoma duomenų bazė ir kuriama schema (migracijos)...")
        sukurti_schema_is_naujo()
    siandien = date.today()

    print("Kuriami vartotojai...")
    admin = _naudotojas("ADMIN", "", "admin@mokykla.lt", "administratorius", "admin123")
    jonas = _naudotojas("Jonas", "Jonaitis", "jonas@mokykla.lt", "mokytojas", "mokytojas123")
    ona = _naudotojas("Ona", "Kazlauskienė", "ona@mokykla.lt", "mokytojas", "mokytojas123",
                      vgk_pareigos="pirmininkas")
    tomas = _naudotojas("Tomas", "Vaitkus", "tomas@mokykla.lt", "mokytojas", "mokytojas123",
                        vgk_pareigos="sekretorius")
    db.session.commit()

    print("Kuriamos klasės...")
    metai = mokslo_metai(siandien)
    klase_5a = Klase(pavadinimas="5A", mokslo_metai=metai, vadovo_id=jonas.id)
    klase_8b = Klase(pavadinimas="8B", mokslo_metai=metai, vadovo_id=ona.id)
    klase_10a = Klase(pavadinimas="10A", mokslo_metai=metai, vadovo_id=tomas.id)
    db.session.add_all([klase_5a, klase_8b, klase_10a])
    db.session.commit()

    print("Kuriami mokiniai...")
    mokiniai = _mokiniai(klase_5a, klase_8b, klase_10a)

    print("Kuriamos tėvų paskyros...")
    petras_tevas = _naudotojas("Petras", "Demo", "tevas@demo.lt", "tevas", "tevas123", telefonas="+37060000000")
    lina = _naudotojas("Lina", "Gricienė", "lina.griciene@demo.lt", "tevas", "tevas123", telefonas="+37061266666")
    db.session.commit()
    petras_tevas.vaikai = [mokiniai["Aistė"], mokiniai["Domas"]]
    lina.vaikai = [mokiniai["Justas"]]
    db.session.commit()

    print("Kuriami Vaiko gerovės komisijos demo duomenys...")
    planuojamas_posedis, ivykes_posedis = _vgk_demo(siandien, ona, tomas, jonas, petras_tevas, mokiniai)

    print("Kuriami skelbimai ir renginiai kalendoriuje...")
    _skelbimai(siandien, admin, jonas, ona, planuojamas_posedis)
    _renginiai(siandien, admin, jonas, ona)

    print("Kuriami diplomai (seminarų pažymėjimai)...")
    _diplomai(siandien, jonas, ona, tomas)

    print("Kuriami pažymų prašymai ir ataskaita...")
    pazyma = _pazymos(admin, petras_tevas, mokiniai)
    ataskaita = parengti_ataskaita(siandien.replace(day=1), siandien, sukure=admin)

    print("Kuriamas duomenų importo pavyzdys...")
    sesija = _importas(admin)

    print("Siunčiami pranešimai (el. laiškai įrašomi į failus)...")
    issiusta = _issiusti_pranesimus(petras_tevas)

    _veiklos_zurnalas(admin, ona, tomas, planuojamas_posedis, ivykes_posedis, pazyma, ataskaita, sesija)

    print("\n" + "=" * 50)
    print("✓ DEMO DUOMENYS SĖKMINGAI SUKURTI!")
    print("=" * 50)
    print("\nPrisijungimo duomenys:\n")
    print("  ADMINISTRATORIUS:")
    print("    El. paštas: admin@mokykla.lt")
    print("    Slaptažodis: admin123\n")
    print("  MOKYTOJAI:")
    print("    jonas@mokykla.lt / mokytojas123")
    print("    ona@mokykla.lt / mokytojas123 (komisijos pirmininkė)")
    print("    tomas@mokykla.lt / mokytojas123 (komisijos sekretorius)\n")
    print("  TĖVAI:")
    print("    tevas@demo.lt / tevas123\n")
    print(f"Sukurta: {User.query.count()} vartotojai, {Klase.query.count()} klasės, "
          f"{Mokinys.query.count()} mokiniai, {Skelbimas.query.count()} skelbimai, "
          f"{Renginys.query.count()} renginiai, {Diplomas.query.count()} diplomai, "
          f"išsiųsta pranešimų: {issiusta}\n")


# --- Mokiniai --------------------------------------------------------------------------

# (vardas, pavardė, gim. data, el. paštas, tel., adresas, motinos vardas, motinos tel., motinos el. paštas,
#  tėvo vardas, tėvo tel., tėvo el. paštas, mokyklos autobusas)
_MOKINIAI = {
    "5A": [
        ("Aistė", "Adomaitytė", date(2014, 3, 15), "aiste.a@mokinys.lt", "+370 600 11111", "Noriūnų k., Kupiškio r.",
         "Jurgita Adomaitienė", "+370 612 11111", "jurgita.a@email.lt",
         "Rimantas Adomaitis", "+370 612 11112", "rimantas.a@email.lt", True),
        ("Domas", "Butkus", date(2014, 5, 22), None, "+370 600 22222", "Mokyklos g. 5, Noriūnai, Kupiškio r.",
         "Inga Butkienė", "+370 612 22222", "inga.b@email.lt",
         "Mindaugas Butkus", "+370 612 22223", None, True),
        ("Eglė", "Čepaitė", date(2014, 1, 10), "egle.c@mokinys.lt", None, "Adomynės k., Kupiškio r.",
         "Vilma Čepienė", "+370 612 33333", "vilma.c@email.lt", None, None, None, False),
        ("Gabrielius", "Dapkus", date(2014, 7, 8), None, "+370 600 44444", "Šimonių k., Kupiškio r.",
         "Daiva Dapkienė", "+370 612 44444", "daiva.d@email.lt",
         "Tomas Dapkus", "+370 612 44445", "tomas.d@email.lt", True),
        ("Ieva", "Eidukaitė", date(2014, 9, 30), "ieva.e@mokinys.lt", "+370 600 55555", "Vilniaus g. 8, Kupiškis",
         "Asta Eidukienė", "+370 612 55555", "asta.e@email.lt",
         "Vytautas Eidukas", "+370 612 55556", None, False),
    ],
    "8B": [
        ("Justas", "Gricius", date(2011, 2, 14), "justas.g@mokinys.lt", "+370 600 66666", "Vytauto g. 12, Kupiškis",
         "Lina Gricienė", "+370 612 66666", "lina.g@email.lt",
         "Arūnas Gricius", "+370 612 66667", "arunas.g@email.lt", False),
        ("Kamilė", "Jasiūnaitė", date(2011, 4, 18), None, "+370 600 77777", "Subačiaus k., Kupiškio r.",
         "Rita Jasiūnienė", "+370 612 77777", "rita.j@email.lt",
         "Donatas Jasiūnas", "+370 612 77778", None, True),
        ("Lukas", "Karpavičius", date(2011, 6, 25), "lukas.k@mokinys.lt", None, "Salamiesčio k., Kupiškio r.",
         "Aurelija Karpavičienė", "+370 612 88888", "aurelija.k@email.lt",
         "Marius Karpavičius", "+370 612 88889", "marius.k@email.lt", False),
        ("Milda", "Liutkutė", date(2011, 8, 3), None, "+370 600 88888", "Gedimino g. 22, Kupiškis",
         "Gintarė Liutkienė", "+370 612 99999", "gintare.l@email.lt", None, None, None, False),
    ],
    "10A": [
        ("Nojus", "Marčiulionis", date(2009, 10, 11), "nojus.m@mokinys.lt", "+370 600 99999", "Skapiškio k., Kupiškio r.",
         "Sandra Marčiulionienė", "+370 613 11111", "sandra.m@email.lt",
         "Arvydas Marčiulionis", "+370 613 11112", "arvydas.m@email.lt", False),
        ("Olga", "Norvilaitė", date(2009, 12, 27), None, "+370 600 12121", "Antašavos k., Kupiškio r.",
         "Tatjana Norvilienė", "+370 613 22222", "tatjana.n@email.lt",
         "Pavel Norvila", "+370 613 22223", None, True),
        ("Paulius", "Petraitis", date(2009, 11, 5), "paulius.p@mokinys.lt", None, "Aušros g. 4, Kupiškis",
         "Rita Petraitienė", "+370 613 33333", "rita.p@email.lt",
         "Saulius Petraitis", "+370 613 33334", "saulius.p@email.lt", False),
    ],
}


def _mokiniai(*klases):
    """Sukuria mokinius ir grąžina žodyną {vardas: mokinys}."""
    pagal_varda = {}
    for klase in klases:
        for (vardas, pavarde, gimimo_data, email, telefonas, adresas, m_vardas, m_tel, m_email,
             t_vardas, t_tel, t_email, autobusas) in _MOKINIAI[klase.pavadinimas]:
            mokinys = Mokinys(
                vardas=vardas, pavarde=pavarde, gimimo_data=gimimo_data,
                email=email, telefonas=telefonas, adresas=adresas,
                motinos_vardas=m_vardas, motinos_telefonas=m_tel, motinos_email=m_email,
                tevo_vardas=t_vardas, tevo_telefonas=t_tel, tevo_email=t_email,
                mokyklos_autobusas=autobusas, klases_id=klase.id,
            )
            db.session.add(mokinys)
            pagal_varda[vardas] = mokinys
    db.session.commit()
    return pagal_varda


# --- Vaiko gerovės komisija ---------------------------------------------------------------

def _vgk_demo(siandien, pirmininke, sekretorius, mokytojas, tevas, mokiniai):
    """Įvykęs posėdis su protokolu ir priemonėmis, posėdis gruodžio mėnesį (po 12 darbo dienų)
    su išsiųstais kvietimais ir naujas kreipimasis. Grąžina (suplanuotas, įvykęs posėdis)."""
    # 1. Domas Butkus: kreipimasis prieš mėnesį, posėdis prieš dvi savaites, trys priemonės
    domas = VgkAtvejis(mokinio_id=mokiniai["Domas"].id, pateike_id=mokytojas.id,
                       priezastis="Aptarta mokinio adaptacijos eiga, sustiprintas individualus darbas "
                                  "su klasės vadovu. Mokymosi sunkumai matematikos pamokose.",
                       busena=VgkAtvejis.TAIKOMOS_PRIEMONES,
                       sukurta=datetime.combine(siandien - timedelta(days=30), time(9, 0)))
    db.session.add(domas)
    ivykes = VgkPosedis(data=siandien - timedelta(days=14), laikas=time(14, 0), vieta="Mokytojų kambarys",
                        busena=VgkPosedis.IVYKES)
    db.session.add(ivykes)  # pirmiau į sesiją, kad svarstymai ir dalyviai būtų įrašyti kartu
    svarstymas = VgkSvarstymas(atvejis=domas, eiles_nr=1,
                               nutarimas="Skirti individualias matematikos konsultacijas, aptarti situaciją su "
                                         "tėvais ir stebėti lankomumą du mėnesius.")
    ivykes.svarstymai.append(svarstymas)
    for naudotojas, vaidmuo in ((pirmininke, "pirmininkas"), (sekretorius, "sekretorius"), (tevas, "tevas")):
        ivykes.dalyviai.append(VgkDalyvis(vartotojo_id=naudotojas.id, vardas_pavarde=naudotojas.pilnas_vardas,
                                          vaidmuo=vaidmuo, dalyvavo=True, pasizadejimas=True))
    svarstymas.priemones.extend([
        VgkPriemone(aprasymas="Individualios matematikos konsultacijos kartą per savaitę",
                    atsakingo_id=mokytojas.id, terminas=siandien + timedelta(days=10)),
        VgkPriemone(aprasymas="Pokalbis su tėvais dėl pagalbos namuose", atsakingo_id=pirmininke.id,
                    terminas=siandien - timedelta(days=3), busena=VgkPriemone.VELUOJA),
        VgkPriemone(aprasymas="Lankomumo stebėsena", atsakingo_id=sekretorius.id,
                    terminas=siandien - timedelta(days=7), busena=VgkPriemone.IVYKDYTA,
                    rezultatas="Lankomumas pagerėjo, praleistų pamokų nebuvo."),
    ])
    db.session.flush()
    ivykes.protokolas = ProtokoloGeneratorius().parengti({"posedis": ivykes}, sukure=sekretorius)
    db.session.commit()

    # 2. Justas Gricius: posėdis gruodžio mėnesį – patvirtinamas per paslaugą, todėl
    #    tikrinamas 5 darbo dienų terminas ir išsiunčiami kvietimai nariams bei tėvams
    justas = VgkAtvejis(mokinio_id=mokiniai["Justas"].id, pateike_id=pirmininke.id,
                        priezastis="Mokymosi sunkumai matematikos pamokose, rekomenduotas papildomas "
                                   "mokytojo konsultavimas.",
                        busena=VgkAtvejis.UZREGISTRUOTAS,
                        sukurta=datetime.combine(siandien - timedelta(days=10), time(10, 30)))
    db.session.add(justas)
    db.session.commit()
    suplanuotas = issaugoti_posedi(
        None, prideti_darbo_dienas(siandien, 12), time(15, 0), "Mokytojų kambarys", [justas],
        {"nariai", f"tevai_{justas.id}", "vadovai"}, kviestiniai="Rasa Petrauskienė, psichologė",
        patvirtinti=True, siandien=siandien)

    # 3. Paulius Petraitis: naujas kreipimasis – pirmininkei pranešama
    pateikti_kreipimasi(sekretorius, mokiniai["Paulius"],
                        "Drausminio pobūdžio incidentas. Siūloma susitarti dėl elgesio sutarties su "
                        "mokiniu ir tėvais.")
    return suplanuotas, ivykes


# --- Skelbimai ir renginiai ----------------------------------------------------------------

def _skelbimai(siandien, admin, jonas, ona, vgk_posedis):
    """Skelbimai; tie, kurie kviečia į renginį, turi datą ir rodomi kalendoriuje."""
    kaledos = date(siandien.year, 12, 18)
    if not 0 < (kaledos - siandien).days <= 60:
        kaledos = siandien + timedelta(days=25)
    taryba = siandien + timedelta(days=3)
    atviros_durys = siandien + timedelta(days=5)
    susirinkimas = siandien + timedelta(days=9)
    seminaras = siandien - timedelta(days=10)

    # (pavadinimas, turinys, autorius, svarbus, matomas tėvams, kategorija, prieš kiek dienų paskelbtas,
    #  renginys kalendoriuje: (data, laikas, vieta) arba None)
    skelbimai = [
        ("Mokytojų tarybos posėdis",
         f"{data_tekstu(taryba).capitalize()} 14.00 mokytojų kambaryje vyks mokytojų tarybos posėdis. "
         "Aptarsime pirmojo trimestro rezultatus ir kalėdinių renginių planą. Dalyvauti kviečiami visi "
         "pedagoginiai darbuotojai.",
         admin, True, False, "administracija", 1, (taryba, time(14, 0), "Mokytojų kambarys")),
        ("Vaiko gerovės komisijos posėdis",
         f"{data_tekstu(vgk_posedis.data).capitalize()} {vgk_posedis.laikas:%H.%M} vyks Vaiko gerovės komisijos "
         "posėdis. Klasių vadovus prašome iki posėdžio pateikti pastebėjimus apie svarstomų mokinių situaciją.",
         ona, True, False, "vgk", 2, (vgk_posedis.data, vgk_posedis.laikas, vgk_posedis.vieta)),
        ("Atvirų durų diena",
         f"Mieli tėvai, kviečiame į atvirų durų dieną {data_tekstu(atviros_durys)} 16.00–19.00. Galėsite "
         "susipažinti su mokyklos veikla, pabendrauti su klasių vadovais ir mokytojais.",
         admin, False, True, "tevams", 3, (atviros_durys, time(16, 0), "Mokyklos aktų salė")),
        ("Tėvų susirinkimas 5A klasėje",
         f"{data_tekstu(susirinkimas).capitalize()} 17.30 kviečiame 5A klasės mokinių tėvus į susirinkimą. "
         "Aptarsime pirmojo trimestro pasiekimus ir ekskursijų planą.",
         jonas, False, True, "tevams", 2, (susirinkimas, time(17, 30), "5A klasės kabinetas")),
        ("Kalėdinis koncertas",
         f"{data_tekstu(kaledos).capitalize()} 18.00 mokyklos salėje vyks kalėdinis koncertas. Pasirodys "
         "mokyklos choras, šokių grupė ir teatro studija. Laukiame ir tėvų!",
         ona, False, True, "renginiai", 5, (kaledos, time(18, 0), "Mokyklos salė")),
        ("Skaitmeninio raštingumo seminaras",
         f"{data_tekstu(seminaras).capitalize()} vyko nuotolinis seminaras „Skaitmeninių įrankių integracija "
         "pamokose“. Dalyvavusiems mokytojams išduoti pažymėjimai – juos rasite skiltyje „Diplomai“.",
         jonas, False, False, "mokytojams", 9, (seminaras, time(13, 0), "Nuotoliniu būdu")),
        ("Valgyklos darbo laikas",
         "Nuo pirmadienio mokyklos valgykla dirba 8.00–15.00. Pietų pertrauka mokiniams – po ketvirtos pamokos.",
         admin, False, True, "bendra", 6, None),
    ]
    for pavadinimas, turinys, autorius, svarbus, tevams, kategorija, dienu_atgal, renginys in skelbimai:
        skelbimas = Skelbimas(pavadinimas=pavadinimas, turinys=turinys, svarbus=svarbus, matomas_tevams=tevams,
                              kategorija=kategorija, vartotojo_id=autorius.id,
                              sukurtas=utc_dabar() - timedelta(days=dienu_atgal))
        db.session.add(skelbimas)
        skelbti("skelbimas_paskelbtas", skelbimas)
        if renginys:
            susieti_su_kalendoriumi(skelbimas, *renginys)
    db.session.commit()


def _renginiai(siandien, admin, jonas, ona):
    """Renginiai kalendoriuje be skelbimo (praėję ir artėjantys)."""
    renginiai = [
        ("Ekskursija į Kupiškio etnografijos muziejų",
         "5A klasės mokinių ekskursija. Išvykstame nuo mokyklos 9.00, grįžtame apie 14.00.",
         siandien + timedelta(days=1), time(9, 0), "Kupiškio etnografijos muziejus", "mokyklos", True, jonas),
        ("Rudens sporto diena", "Sporto varžybos 5–10 klasių mokiniams.",
         siandien - timedelta(days=12), time(10, 0), "Mokyklos stadionas", "mokyklos", True, admin),
        ("Lietuvių kalbos olimpiada (mokyklos etapas)", "Olimpiadoje dalyvauja 8–10 klasių mokiniai.",
         siandien + timedelta(days=16), time(9, 0), "Informatikos kabinetas", "mokyklos", False, ona),
    ]
    atostogos = date(siandien.year, 12, 23)
    if 0 < (atostogos - siandien).days <= 60:
        renginiai.append(("Žiemos (Kalėdų) atostogos", "Mokiniams – žiemos atostogos.",
                          atostogos, None, None, "svente", True, admin))
    for pavadinimas, aprasymas, data, laikas, vieta, kategorija, tevams, autorius in renginiai:
        renginys = Renginys(pavadinimas=pavadinimas, aprasymas=aprasymas, pradzios_data=data, pradzios_laikas=laikas,
                            vieta=vieta, kategorija=kategorija, matomas_tevams=tevams, vartotojo_id=autorius.id)
        if kategorija == "svente":
            renginys.pabaigos_data = date(atostogos.year + 1, 1, 2)
        db.session.add(renginys)
        skelbti("renginys_sukurtas", renginys)
    db.session.commit()


# --- Diplomai ------------------------------------------------------------------------------

def _pazymejimo_pdf(kelias, vardas, seminaras, valandos, data, numeris):
    """Seminaro pažymėjimas (A4 gulsčias) su lietuviškomis raidėmis."""
    _uzregistruoti_sriftus()
    plotis, aukstis = landscape(A4)
    pdf = canvas.Canvas(kelias, pagesize=(plotis, aukstis))
    pdf.setTitle(f"Pažymėjimas – {seminaras}")
    pdf.setStrokeColorRGB(0.62, 0.07, 0.22)
    pdf.setLineWidth(3)
    pdf.rect(28, 28, plotis - 56, aukstis - 56)
    pdf.setLineWidth(1)
    pdf.rect(36, 36, plotis - 72, aukstis - 72)
    eilutes = [
        (SRIFTAS, 12, aukstis - 90, "Kvalifikacijos tobulinimo centras · demonstracinis dokumentas"),
        (SRIFTAS_PARYSKINTAS, 32, aukstis - 160, "PAŽYMĖJIMAS"),
        (SRIFTAS, 14, aukstis - 210, "Patvirtinama, kad"),
        (SRIFTAS_PARYSKINTAS, 24, aukstis - 250, vardas),
        (SRIFTAS, 14, aukstis - 290, f"dalyvavo {valandos} akademinių valandų kvalifikacijos tobulinimo seminare"),
        (SRIFTAS_PARYSKINTAS, 17, aukstis - 322, f"„{seminaras}“"),
    ]
    for sriftas, dydis, y, tekstas in eilutes:
        pdf.setFont(sriftas, dydis)
        pdf.drawCentredString(plotis / 2, y, tekstas)
    pdf.setFont(SRIFTAS, 11)
    pdf.drawString(80, 80, f"Išdavimo data: {data:%Y-%m-%d}")
    pdf.drawRightString(plotis - 80, 80, f"Registracijos numeris: {numeris}")
    pdf.showPage()
    pdf.save()


def _diplomai(siandien, jonas, ona, tomas):
    katalogas = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(katalogas, exist_ok=True)
    pazymejimai = [
        (jonas, "Skaitmeninių įrankių integracija pamokose", 6, siandien - timedelta(days=10)),
        (ona, "Vaiko gerovės komisijos veiklos organizavimas", 8, siandien - timedelta(days=40)),
        (tomas, "Pirmoji pagalba mokykloje", 8, siandien - timedelta(days=75)),
    ]
    for nr, (mokytojas, seminaras, valandos, data) in enumerate(pazymejimai, start=1):
        failas = f"demo_pazymejimas_{nr}.pdf"
        numeris = f"KT-{data.year}-{100 + nr}"
        _pazymejimo_pdf(os.path.join(katalogas, failas), mokytojas.pilnas_vardas, seminaras, valandos, data, numeris)
        db.session.add(Diplomas(
            pavadinimas=f"Pažymėjimas: {seminaras}", seminaras=seminaras, isdavimo_data=data,
            aprasymas=f"{valandos} akademinių valandų kvalifikacijos tobulinimo seminaras. Registracijos numeris {numeris}.",
            failo_kelias=failas, originalus_failo_vardas=f"pazymejimas_{numeris}.pdf", failo_tipas="pdf",
            vartotojo_id=mokytojas.id,
        ))
    db.session.commit()


# --- Pažymos, importas, pranešimai, žurnalas -----------------------------------------------

def _pazymos(admin, tevas, mokiniai):
    """Įvykdytas (su PDF), atmestas ir laukiantis pažymų prašymai. Grąžina parengtą pažymą."""
    ivykdytas = pateikti_prasyma(tevas, mokiniai["Aistė"], "Pateikti „Sodrai“")
    pazyma = patvirtinti_prasyma(ivykdytas, admin)
    atmestas = pateikti_prasyma(tevas, mokiniai["Domas"], "Būrelio lankymui", "krepšinio būrelis")
    atmesti_prasyma(atmestas, admin, "Būrelio lankymą patvirtina būrelio vadovas – kreipkitės į jį tiesiogiai.")
    pateikti_prasyma(tevas, mokiniai["Domas"], "Darbdaviui")
    return pazyma


def _importas(admin):
    """Užbaigtas importas: 3 nauji mokiniai (2 tėvų paskyros su kvietimais), dublikatas ir klaida."""
    eilutes = [
        "Vardas;Pavardė;Gimimo data;Klasė;Tėvo (globėjo) vardas, pavardė;Tėvo (globėjo) el. paštas",
        "Ugnė;Kairytė;2014-03-21;5A;Rasa Kairienė;rasa.kairiene@demo.lt",
        "Rokas;Žemaitis;2014-06-02;5A;Darius Žemaitis;darius.zemaitis@demo.lt",
        "Emilija;Vasiliauskaitė;2014-09-17;5A;;",
        "Aistė;Adomaitytė;2014-03-15;5A;;",
        "Matas;Petrauskas;2014-02-31;5A;;",
    ]
    vykdytojas = ImportoVykdytojas()
    sesija = vykdytojas.nuskaityti("mokiniai_5A_papildymas.csv", "\n".join(eilutes).encode("utf-8"), admin)
    vykdytojas.tikrinti(sesija)
    db.session.commit()
    return vykdytojas.irasyti(sesija, admin)


def _issiusti_pranesimus(tevas):
    """Priminimai ir eilės išsiuntimas. El. laiškai visada įrašomi į failus (ne SMTP),
    kad demonstraciniai duomenys niekada nesiųstų tikrų laiškų."""
    PriminimuKurejas().sukurti_priminimus()
    nustatymai = {"MAIL_BACKEND": "failai", "MAIL_FAILU_KATALOGAS": current_app.config["MAIL_FAILU_KATALOGAS"],
                  "MAIL_SENDER": current_app.config.get("MAIL_SENDER")}
    issiusta = PranesimuSiuntejas(kanalai=[ElPastoKanalas(nustatymai), SistemosKanalas()]).siusti_eile(laiko_riba=300)
    # Vienas nepavykęs laiškas – kad siuntimo žurnale matytųsi klaida ir pakartojimo mygtukas
    db.session.add(EilesIrasas(
        gavejo_id=tevas.id, kanalas="el_pastas", unikalus_raktas="demo/nepavykes-laiskas",
        tema="Naujas skelbimas: Valgyklos darbo laikas",
        tekstas="Sveiki, mokykla paskelbė naują skelbimą „Valgyklos darbo laikas“.",
        busena=EilesIrasas.NEPAVYKO, bandymai=4, siusti_po=utc_dabar() - timedelta(hours=2),
        klaida="El. laiško išsiųsti nepavyko: SMTP serveris nepasiekiamas (demonstracinis įrašas)",
    ))
    db.session.commit()
    return issiusta


def _veiklos_zurnalas(admin, ona, tomas, suplanuotas, ivykes, pazyma, ataskaita, sesija):
    irasai = [
        (tomas, "vgk_protokolas", "vgk_posedis", ivykes.id, "Parengtas posėdžio protokolas", 14),
        (ona, "vgk_posedis_suplanuotas", "vgk_posedis", suplanuotas.id, "Suplanuotas komisijos posėdis", 0),
        (ona, "vgk_perziura", "vgk_atvejis", suplanuotas.svarstymai[0].atvejo_id, "Peržiūrėtas atvejis", 0),
        (admin, "pazyma_parengta", "dokumentas", pazyma.id, f"Parengta pažyma {pazyma.numeris}", 0),
        (admin, "ataskaita_parengta", "dokumentas", ataskaita.id, f"Parengta ataskaita {ataskaita.numeris}", 0),
        (admin, "importas_baigtas", "importo_sesija", sesija.id, f"Importuota: {sesija.failo_vardas}", 0),
    ]
    for naudotojas, veiksmas, tipas, objekto_id, aprasymas, dienu_atgal in irasai:
        db.session.add(VeiklosZurnalas(vartotojo_id=naudotojas.id, veiksmas=veiksmas, objekto_tipas=tipas,
                                       objekto_id=objekto_id, aprasymas=aprasymas, ip_adresas="127.0.0.1",
                                       laikas=utc_dabar() - timedelta(days=dienu_atgal, minutes=5)))
    db.session.commit()


if __name__ == "__main__":
    uzpildyti_db()
