"""FR-D04 su PostgreSQL: lygiagrečiai generuojami dokumentai negauna vienodų numerių.

Dvi gijos (lyg du administratoriai) vienu metu kuria pažymas. Skaitiklio eilutė
užrakinama (SELECT ... FOR UPDATE), todėl numeriai nesidubliuoja ir nepraleidžiami.
"""
import threading
from datetime import date

from models import Dokumentas, Mokinys, db
from services.dokumentai import PazymosGeneratorius


def test_lygiagretus_numeravimas(app, vaikas, tmp_path):
    app.config["DOKUMENTU_KATALOGAS"] = str(tmp_path)
    mokinio_id = vaikas.id
    db.session.remove()
    startas = threading.Barrier(2)
    klaidos = []

    def kurti_dokumentus():
        try:
            with app.app_context():
                startas.wait()
                for _ in range(5):
                    mokinys = db.session.get(Mokinys, mokinio_id)
                    PazymosGeneratorius().parengti({"mokinys": mokinys, "paskirtis": "Darbdaviui"}, mokinys=mokinys)
                    db.session.commit()
                db.session.remove()
        except Exception as klaida:
            klaidos.append(klaida)

    gijos = [threading.Thread(target=kurti_dokumentus) for _ in range(2)]
    for gija in gijos:
        gija.start()
    for gija in gijos:
        gija.join(timeout=60)

    assert not klaidos
    metai = date.today().year
    numeriai = sorted(d.numeris for d in Dokumentas.query.all())
    assert numeriai == [f"PZ-{metai}-{nr:04d}" for nr in range(1, 11)]
