"""Numatytieji pranešimų šablonai ir automatizavimo taisyklės.

Duomenų migracija: įrašomi pradiniai šablonai ir taisyklės, kad automatizavimas
veiktų iš karto po diegimo ar atnaujinimo (ne tik užpildžius demonstracinius
duomenis). Administratorius vėliau juos gali keisti sistemoje.

Pirmosios penkios taisyklės atitinka aprašo 15 pav. maketą. VGK el. laiškuose
pateikiama tik posėdžio data, laikas, vieta ir nuoroda į sistemą (NFR-10).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-20 20:00:00
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

JSON_LAUKAS = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

pranesimu_sablonai = sa.table(
    "pranesimu_sablonai",
    sa.column("id", sa.Integer),
    sa.column("kodas", sa.String),
    sa.column("pavadinimas", sa.String),
    sa.column("tema", sa.String),
    sa.column("tekstas", sa.Text),
    sa.column("atnaujinta", sa.DateTime),
)
automatizavimo_taisykles = sa.table(
    "automatizavimo_taisykles",
    sa.column("pavadinimas", sa.String),
    sa.column("ivykio_tipas", sa.String),
    sa.column("salyga", JSON_LAUKAS),
    sa.column("gavejai", sa.String),
    sa.column("kanalas", sa.String),
    sa.column("poslinkis_d", sa.Integer),
    sa.column("sablono_id", sa.Integer),
    sa.column("aktyvi", sa.Boolean),
)

PABAIGA = "\n\nŠis laiškas išsiųstas automatiškai, į jį atsakyti nereikia."

# (kodas, pavadinimas, tema, tekstas)
SABLONAI = [
    ("skelbimas_tevams", "Naujas skelbimas tėvams",
     "Naujas skelbimas: {{ skelbimas.pavadinimas }}",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "{{ mokykla.pavadinimas }} paskelbė naują skelbimą „{{ skelbimas.pavadinimas }}“.\n\n"
     "{{ skelbimas.turinys }}\n\n"
     "Skelbimą galite peržiūrėti sistemoje: {{ nuoroda }}" + PABAIGA),
    ("renginio_priminimas", "Priminimas apie renginį",
     "Primename: {{ renginys.pavadinimas }} ({{ renginys.data }})",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "primename, kad {{ renginys.data }}{% if renginys.laikas %} {{ renginys.laikas }} val.{% endif %} "
     "vyks renginys „{{ renginys.pavadinimas }}“.\n"
     "{% if renginys.vieta %}Vieta: {{ renginys.vieta }}.\n{% endif %}\n"
     "Daugiau informacijos: {{ nuoroda }}" + PABAIGA),
    ("vgk_kvietimas", "Komisijos posėdžio kvietimas",
     "Kvietimas į Vaiko gerovės komisijos posėdį {{ posedis.data }}",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "kviečiame dalyvauti Vaiko gerovės komisijos posėdyje.\n\n"
     "Data: {{ posedis.data }}\nLaikas: {{ posedis.laikas }}\nVieta: {{ posedis.vieta }}\n\n"
     "Išsamesnė informacija pateikiama prisijungus prie sistemos: {{ nuoroda }}\n"
     "Dėl duomenų apsaugos svarstymo informacija el. laiške nepateikiama." + PABAIGA),
    ("priemones_priminimas", "Priemonės termino priminimas",
     "Artėja priemonės įvykdymo terminas ({{ priemone.terminas }})",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "Jums paskirtos Vaiko gerovės komisijos priemonės įvykdymo terminas – {{ priemone.terminas }}.\n"
     "Įvykdymą pažymėkite sistemoje: {{ nuoroda }}"),
    ("menesio_suvestine", "Mėnesio suvestinė",
     "Mėnesio suvestinė: {{ suvestine.laikotarpis }}",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "parengta praėjusio mėnesio suvestinė (dokumento nr. {{ suvestine.numeris }}).\n"
     "Ją galite peržiūrėti dokumentų registre: {{ nuoroda }}" + PABAIGA),
    ("vgk_priminimas", "Komisijos posėdžio priminimas",
     "Primename: Vaiko gerovės komisijos posėdis {{ posedis.data }} {{ posedis.laikas }}",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "primename, kad {{ posedis.data }} {{ posedis.laikas }} val. vyks Vaiko gerovės komisijos posėdis.\n"
     "Vieta: {{ posedis.vieta }}.\n\n"
     "Išsamesnė informacija – sistemoje: {{ nuoroda }}" + PABAIGA),
    ("vgk_atsaukimas", "Komisijos posėdžio atšaukimas",
     "Atšauktas Vaiko gerovės komisijos posėdis {{ posedis.data }}",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "{{ posedis.data }} {{ posedis.laikas }} val. numatytas Vaiko gerovės komisijos posėdis atšauktas.\n"
     "Apie naują posėdžio datą informuosime atskirai." + PABAIGA),
    ("vgk_kreipimasis", "Naujas kreipimasis į komisiją",
     "Naujas kreipimasis į Vaiko gerovės komisiją (nr. {{ atvejis.numeris }})",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "{{ atvejis.data }} užregistruotas naujas kreipimasis į Vaiko gerovės komisiją (nr. {{ atvejis.numeris }}).\n"
     "Jį galite peržiūrėti sistemoje: {{ nuoroda }}"),
    ("priemone_veluoja", "Vėluojanti priemonė",
     "Vėluoja priemonės įvykdymas (terminas {{ priemone.terminas }})",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "Vaiko gerovės komisijos priemonės įvykdymo terminas ({{ priemone.terminas }}) praėjo, "
     "o priemonė dar nepažymėta įvykdyta.\nPeržiūrėti: {{ nuoroda }}"),
    ("pazymos_prasymas_naujas", "Naujas pažymos prašymas",
     "Naujas pažymos prašymas: {{ prasymas.mokinys }}",
     "Tėvai pateikė pažymos prašymą apie mokinį {{ prasymas.mokinys }} (paskirtis: {{ prasymas.paskirtis }}).\n"
     "Prašymą galite peržiūrėti: {{ nuoroda }}"),
    ("pazyma_parengta", "Pažyma parengta",
     "Pažyma parengta ({{ prasymas.numeris }})",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "Jūsų užsakyta pažyma apie {{ prasymas.mokinys }} (paskirtis: {{ prasymas.paskirtis }}) parengta. "
     "Dokumento numeris – {{ prasymas.numeris }}.\n"
     "Pažymą galite atsisiųsti: {{ nuoroda }}" + PABAIGA),
    ("pazyma_atmesta", "Pažymos prašymas atmestas",
     "Pažymos prašymas atmestas",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "Jūsų prašymas parengti pažymą apie {{ prasymas.mokinys }} (paskirtis: {{ prasymas.paskirtis }}) atmestas.\n"
     "Priežastis: {{ prasymas.priezastis }}\n\n"
     "Prašymų būsenas galite matyti sistemoje: {{ nuoroda }}" + PABAIGA),
    ("importas_baigtas", "Importas baigtas",
     "Duomenų importas baigtas: {{ importas.failo_vardas }}",
     "Failo {{ importas.failo_vardas }} importas baigtas: įrašyta {{ importas.tinkamu_sk }} "
     "iš {{ importas.eiluciu_sk }} eilučių, su klaidomis {{ importas.klaidu_sk }}.\n"
     "Ataskaita: {{ nuoroda }}"),
    ("renginys_naujas", "Naujas renginys",
     "Naujas renginys: {{ renginys.pavadinimas }} ({{ renginys.data }})",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "{{ renginys.data }}{% if renginys.laikas %} {{ renginys.laikas }} val.{% endif %} vyks renginys "
     "„{{ renginys.pavadinimas }}“.\n{% if renginys.vieta %}Vieta: {{ renginys.vieta }}.\n{% endif %}\n"
     "{{ renginys.aprasymas }}\n\nDaugiau informacijos: {{ nuoroda }}" + PABAIGA),
    ("renginio_pakeitimas", "Renginio pakeitimas",
     "Pasikeitė renginio informacija: {{ renginys.pavadinimas }}",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "pasikeitė renginio „{{ renginys.pavadinimas }}“ informacija. Dabartinė data: {{ renginys.data }}"
     "{% if renginys.laikas %} {{ renginys.laikas }} val.{% endif %}"
     "{% if renginys.vieta %}, vieta: {{ renginys.vieta }}{% endif %}.\n\n"
     "Daugiau informacijos: {{ nuoroda }}" + PABAIGA),
    ("renginio_atsaukimas", "Renginio atšaukimas",
     "Renginys atšauktas: {{ renginys.pavadinimas }}",
     "Sveiki, {{ gavejas.vardas }},\n\n"
     "{{ renginys.data }} numatytas renginys „{{ renginys.pavadinimas }}“ atšauktas." + PABAIGA),
]

TEVAMS_MATOMAS = {"matomas_tevams": True}

# (pavadinimas, įvykio tipas, sąlyga, gavėjai, kanalai, poslinkis dienomis, šablono kodas, aktyvi)
TAISYKLES = [
    ("Naujas skelbimas tėvams", "skelbimas_paskelbtas", TEVAMS_MATOMAS, "tevai", "el_pastas", 0,
     "skelbimas_tevams", True),
    ("Priminimas apie renginį", "renginys_artejantis", TEVAMS_MATOMAS, "tevai", "el_pastas", 1,
     "renginio_priminimas", True),
    ("Komisijos posėdžio kvietimas", "vgk_posedis_suplanuotas", None, "posedzio_dalyviai",
     "el_pastas,sistema", 0, "vgk_kvietimas", True),
    ("Priemonės termino priminimas", "priemones_terminas_artejantis", None, "atsakingas", "sistema", 2,
     "priemones_priminimas", True),
    ("Mėnesio suvestinė", "menesio_suvestine", None, "administratoriai", "el_pastas", 0,
     "menesio_suvestine", False),
    ("Komisijos posėdžio priminimas", "vgk_posedis_artejantis", None, "posedzio_dalyviai",
     "el_pastas,sistema", 1, "vgk_priminimas", True),
    ("Komisijos posėdžio atšaukimas", "vgk_posedis_atsauktas", None, "posedzio_dalyviai",
     "el_pastas,sistema", 0, "vgk_atsaukimas", True),
    ("Naujas kreipimasis į komisiją", "vgk_atvejis_uzregistruotas", None, "vgk_pirmininkas",
     "el_pastas,sistema", 0, "vgk_kreipimasis", True),
    ("Vėluojanti priemonė", "priemone_veluoja", None, "vgk_pirmininkas", "sistema", 0,
     "priemone_veluoja", True),
    ("Naujas pažymos prašymas", "pazymos_prasymas_pateiktas", None, "administratoriai", "sistema", 0,
     "pazymos_prasymas_naujas", True),
    ("Pažyma parengta", "pazymos_prasymas_ivykdytas", None, "prasymo_teikejas", "el_pastas,sistema", 0,
     "pazyma_parengta", True),
    ("Pažymos prašymas atmestas", "pazymos_prasymas_atmestas", None, "prasymo_teikejas",
     "el_pastas,sistema", 0, "pazyma_atmesta", True),
    ("Importas baigtas", "importas_baigtas", None, "iniciatorius", "sistema", 0, "importas_baigtas", True),
    ("Naujas renginys tėvams", "renginys_sukurtas", TEVAMS_MATOMAS, "tevai", "el_pastas", 0,
     "renginys_naujas", False),
    ("Pakeistas renginys", "renginys_pakeistas", TEVAMS_MATOMAS, "tevai", "el_pastas", 0,
     "renginio_pakeitimas", False),
    ("Atšauktas renginys", "renginys_atsauktas", TEVAMS_MATOMAS, "tevai", "el_pastas", 0,
     "renginio_atsaukimas", False),
]


def upgrade():
    rysys = op.get_bind()
    dabar = datetime.now(timezone.utc).replace(tzinfo=None)

    esami = {eil.kodas for eil in rysys.execute(sa.select(pranesimu_sablonai.c.kodas))}
    nauji = [
        {"kodas": kodas, "pavadinimas": pavadinimas, "tema": tema, "tekstas": tekstas, "atnaujinta": dabar}
        for kodas, pavadinimas, tema, tekstas in SABLONAI if kodas not in esami
    ]
    if nauji:
        op.bulk_insert(pranesimu_sablonai, nauji)

    sablonu_id = dict(rysys.execute(sa.select(pranesimu_sablonai.c.kodas, pranesimu_sablonai.c.id)).all())
    op.bulk_insert(automatizavimo_taisykles, [
        {"pavadinimas": pavadinimas, "ivykio_tipas": tipas, "salyga": salyga, "gavejai": gavejai,
         "kanalas": kanalas, "poslinkis_d": poslinkis, "sablono_id": sablonu_id[kodas], "aktyvi": aktyvi}
        for pavadinimas, tipas, salyga, gavejai, kanalas, poslinkis, kodas, aktyvi in TAISYKLES
    ])


def downgrade():
    rysys = op.get_bind()
    kodai = [kodas for kodas, *_ in SABLONAI]
    sablonu_id = [eil.id for eil in rysys.execute(
        sa.select(pranesimu_sablonai.c.id).where(pranesimu_sablonai.c.kodas.in_(kodai)))]
    if sablonu_id:
        rysys.execute(sa.text(
            "UPDATE pranesimu_eile SET taisykles_id = NULL WHERE taisykles_id IN "
            "(SELECT id FROM automatizavimo_taisykles WHERE sablono_id IN :ids)"
        ).bindparams(sa.bindparam("ids", expanding=True)), {"ids": sablonu_id})
        rysys.execute(
            automatizavimo_taisykles.delete().where(automatizavimo_taisykles.c.sablono_id.in_(sablonu_id)))
        rysys.execute(pranesimu_sablonai.delete().where(pranesimu_sablonai.c.id.in_(sablonu_id)))
