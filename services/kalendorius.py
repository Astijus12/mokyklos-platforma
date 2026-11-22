"""Darbo dienų skaičiavimas pagal Lietuvos švenčių dienas.

Naudojama VGK posėdžio termino patikrai (FR-V04: kvietimai ne vėliau kaip prieš
5 darbo dienas) ir priminimams (FR-V05: likus 1 darbo dienai; FR-V09).

Švenčių dienos – pagal Darbo kodekso 123 straipsnį. Kilnojamos šventės, kurios
visada būna sekmadienį (Velykos, Motinos ir Tėvo dienos), darbo dienų skaičiui
įtakos neturi, todėl atskirai skaičiuojama tik Velykų antroji diena (pirmadienis).
"""
from datetime import date, datetime, timedelta
from functools import lru_cache


def data_is_formos(reiksme):
    """Formos lauko reikšmė MMMM-MM-DD -> date (netinkama ar tuščia -> None)."""
    try:
        return datetime.strptime(reiksme, "%Y-%m-%d").date() if reiksme else None
    except ValueError:
        return None


def laikas_is_formos(reiksme):
    """Formos lauko reikšmė VV:MM -> time (netinkama ar tuščia -> None)."""
    try:
        return datetime.strptime(reiksme, "%H:%M").time() if reiksme else None
    except ValueError:
        return None

# (mėnuo, diena)
_FIKSUOTOS_SVENTES = (
    (1, 1),    # Naujųjų metų diena
    (2, 16),   # Lietuvos valstybės atkūrimo diena
    (3, 11),   # Lietuvos nepriklausomybės atkūrimo diena
    (5, 1),    # Tarptautinė darbo diena
    (6, 24),   # Rasos ir Joninių diena
    (7, 6),    # Valstybės (Lietuvos karaliaus Mindaugo karūnavimo) diena
    (8, 15),   # Žolinė
    (11, 1),   # Visų Šventųjų diena
    (11, 2),   # Mirusiųjų atminimo (Vėlinių) diena
    (12, 24),  # Kūčios
    (12, 25),  # Kalėdos
    (12, 26),  # Kalėdų antroji diena
)


def velyku_sekmadienis(metai):
    """Velykų sekmadienio data (Gauso / „anoniminis Grigaliaus“ algoritmas)."""
    a = metai % 19
    b, c = divmod(metai, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741 – algoritmo žymėjimas
    m = (a + 11 * h + 22 * l) // 451
    menuo, diena = divmod(h + l - 7 * m + 114, 31)
    return date(metai, menuo, diena + 1)


@lru_cache(maxsize=32)
def sventes(metai):
    """Visos tų metų švenčių dienos, į kurias atsižvelgiama skaičiuojant darbo dienas."""
    dienos = {date(metai, menuo, diena) for menuo, diena in _FIKSUOTOS_SVENTES}
    dienos.add(velyku_sekmadienis(metai) + timedelta(days=1))  # Velykų antroji diena
    return frozenset(dienos)


def ar_darbo_diena(diena):
    """Darbo diena – pirmadienis–penktadienis, išskyrus švenčių dienas."""
    return diena.weekday() < 5 and diena not in sventes(diena.year)


def darbo_dienos_iki(data, nuo=None):
    """Kiek darbo dienų liko iki datos: skaičiuojamos dienos po „nuo“ iki „data“ imtinai.

    Pavyzdžiui, šiandien pirmadienis, posėdis kitą pirmadienį – liko 5 darbo
    dienos (antradienis–penktadienis ir posėdžio pirmadienis). Jei data jau
    praėjo arba yra šiandien, grąžinamas 0.
    """
    nuo = nuo or date.today()
    kiekis = 0
    diena = nuo + timedelta(days=1)
    while diena <= data:
        if ar_darbo_diena(diena):
            kiekis += 1
        diena += timedelta(days=1)
    return kiekis


def prideti_darbo_dienas(nuo, kiekis):
    """Data, kuri yra po nurodyto darbo dienų skaičiaus (pvz., artimiausia leistina posėdžio data)."""
    diena = nuo
    while kiekis > 0:
        diena += timedelta(days=1)
        if ar_darbo_diena(diena):
            kiekis -= 1
    return diena
