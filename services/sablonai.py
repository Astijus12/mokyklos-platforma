"""Pranešimų šablonų apdorojimas saugioje Jinja2 aplinkoje (FR-A03, NFR-07).

Šablonus redaguoja administratorius, todėl jie vykdomi SandboxedEnvironment
aplinkoje: šablonas negali kviesti pavojingų metodų ar pasiekti vidinių Python
objektų (pvz., {{ x.__class__ }}). Be to, šablonams perduodami ne duomenų bazės
objektai, o paprasti žodynai tik su leistinais laukais (žr. services/ivykiai.py),
todėl per šabloną negalima pasiekti, pavyzdžiui, naudotojo slaptažodžio maišos.
"""
from jinja2 import StrictUndefined, TemplateError, Undefined
from jinja2.sandbox import SandboxedEnvironment


class SablonoKlaida(Exception):
    """Šablone yra sintaksės klaida, nežinomas kintamasis arba draudžiamas veiksmas."""


# Pavyzdiniai duomenys šablono peržiūrai ir patikrai. Juose yra visi kintamieji,
# kuriuos gali gauti šablonai (konkretus įvykis perduoda tik dalį jų).
PAVYZDINIAI_DUOMENYS = {
    "gavejas": {"vardas": "Mindaugas", "pavarde": "Butkus", "pilnas_vardas": "Mindaugas Butkus"},
    "mokykla": {"pavadinimas": "Noriūnų Jono Černiaus mokykla"},
    "nuoroda": "http://127.0.0.1:5000/tevams/skelbimai",
    "skelbimas": {
        "pavadinimas": "Atvirų durų diena",
        "turinys": "Kviečiame tėvus į atvirų durų dieną lapkričio 25 d. 16.00 val.",
        "kategorija": "renginiai",
        "svarbus": False,
        "data": "2026-11-20",
    },
    "renginys": {
        "pavadinimas": "Kalėdinis koncertas",
        "aprasymas": "Pasirodys mokyklos choras ir teatro studija.",
        "data": "2026-12-18",
        "laikas": "18:00",
        "vieta": "Mokyklos aktų salė",
        "kategorija": "mokyklos",
    },
    "posedis": {"data": "2026-12-08", "laikas": "14:00", "vieta": "Mokytojų kambarys"},
    "atvejis": {"numeris": "2026-07", "data": "2026-11-18"},
    "priemone": {"terminas": "2026-12-20"},
    "prasymas": {
        "paskirtis": "Sporto būreliui",
        "busena": "Įvykdytas",
        "mokinys": "Domas Butkus",
        "numeris": "PZ-2026-0042",
        "priezastis": "",
    },
    "importas": {"failo_vardas": "mokiniai_2026.xlsx", "eiluciu_sk": 48, "tinkamu_sk": 45, "klaidu_sk": 3},
    "suvestine": {"laikotarpis": "2026 m. lapkritis", "numeris": "AT-2026-0011"},
    "paskyra": {"el_pastas": "tevas@pavyzdys.lt"},
}


def _aplinka(neapibrezti):
    return SandboxedEnvironment(
        undefined=neapibrezti,
        autoescape=False,     # laiškai siunčiami kaip paprastas tekstas
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
    )


class SablonuApdorotojas:
    """Iš šablono ir duomenų suformuoja pranešimo temą ir tekstą."""

    def __init__(self):
        # Siunčiant nežinomas kintamasis tampa tuščia eilute (pranešimas vis tiek išsiunčiamas),
        # o tikrinant ir peržiūrint – klaida, kad administratorius ją pamatytų iš karto.
        self._aplinka = _aplinka(Undefined)
        self._grieztoji = _aplinka(StrictUndefined)

    @staticmethod
    def _sutvarkyti(tema, tekstas):
        # Tema – viena eilutė: el. laiško antraštėje eilučių lūžiai neleidžiami
        return " ".join(tema.split()), tekstas.strip()

    def _atvaizduoti(self, aplinka, tema, tekstas, duomenys):
        try:
            rez_tema = aplinka.from_string(tema).render(duomenys)
            rez_tekstas = aplinka.from_string(tekstas).render(duomenys)
        except TemplateError as klaida:
            raise SablonoKlaida(str(klaida)) from klaida
        except Exception as klaida:
            # Pvz., smėliadėžė per didelį range() sustabdo OverflowError klaida, o dalyba
            # iš nulio – ZeroDivisionError. Blogas šablonas neturi nutraukti įvykio išsaugojimo.
            raise SablonoKlaida(f"{type(klaida).__name__}: {klaida}") from klaida
        return self._sutvarkyti(rez_tema, rez_tekstas)

    def formuoti(self, sablonas, duomenys):
        """Grąžina porą (tema, tekstas) konkrečiam gavėjui."""
        return self._atvaizduoti(self._aplinka, sablonas.tema, sablonas.tekstas, duomenys)

    def perziura(self, sablonas):
        """Šablonas su pavyzdiniais duomenimis (FR-A03). Klaidos atveju – SablonoKlaida."""
        return self._atvaizduoti(self._grieztoji, sablonas.tema, sablonas.tekstas, PAVYZDINIAI_DUOMENYS)

    def patikrinti(self, sablonas):
        """Grąžina klaidos tekstą arba None, jei šablonas tinkamas (naudojama išsaugant)."""
        try:
            self.perziura(sablonas)
        except SablonoKlaida as klaida:
            return str(klaida)
        return None
