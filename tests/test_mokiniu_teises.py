"""Teisės: mokytojas tvarko tik savo klasės mokinius (kurių klasės vadovas), kitų – tik peržiūri.

Administratorius tvarko visus mokinius; komisijos pareigos šių teisių nekeičia.
"""
import io
import re

import pytest

from models import Klase, Mokinys, User, db

pytestmark = pytest.mark.integration

MOKINIO_FORMA = {"vardas": "Naujas", "pavarde": "Mokinys"}


@pytest.fixture
def kita_klase(db_session):
    vadove = User(vardas="Rasa", pavarde="Vadovė", email="rasa@test.lt", role="mokytojas")
    vadove.nustatyti_slaptazodi("mokytojas123")
    db_session.add(vadove)
    db_session.commit()
    kita = Klase(pavadinimas="8B", mokslo_metai="2026-2027", vadovo_id=vadove.id)
    db_session.add(kita)
    db_session.commit()
    return kita


@pytest.fixture
def kitas_mokinys(db_session, kita_klase):
    mokinys = Mokinys(vardas="Kitas", pavarde="Mokinys", klases_id=kita_klase.id, mokyklos_autobusas=False)
    db_session.add(mokinys)
    db_session.commit()
    return mokinys


@pytest.fixture
def mokytojo_klientas(client, mokytojas, klase):
    """Prisijungęs mokytojas – klasės „5A“ vadovas (fiksatorius klase)."""
    client.post("/login", data={"email": mokytojas.email, "slaptazodis": "mokytojas123"})
    return client


def test_tvarkomos_klases(mokytojas, klase, kita_klase, admin):
    assert mokytojas.tvarkomu_klasiu_ids == {klase.id}
    assert admin.tvarkomu_klasiu_ids == {klase.id, kita_klase.id}
    komisijos_narys = User(vardas="Ona", pavarde="Narė", email="ona@test.lt", role="mokytojas",
                           vgk_pareigos="pirmininkas")
    komisijos_narys.nustatyti_slaptazodi("x")
    db.session.add(komisijos_narys)
    db.session.commit()
    assert komisijos_narys.tvarkomu_klasiu_ids == set()  # pareigos komisijoje teisių nesuteikia


class TestMokytojas:
    def test_savo_klases_mokini_gali_redaguoti(self, mokytojo_klientas, vaikas, klase):
        atsakymas = mokytojo_klientas.post(f"/mokiniai/{vaikas.id}/redaguoti",
                                           data={**MOKINIO_FORMA, "klases_id": klase.id})
        assert atsakymas.status_code == 302
        assert db.session.get(Mokinys, vaikas.id).vardas == "Naujas"

    def test_kitos_klases_mokinio_keisti_negali(self, mokytojo_klientas, kitas_mokinys, kita_klase):
        assert mokytojo_klientas.get(f"/mokiniai/{kitas_mokinys.id}/redaguoti").status_code == 403
        assert mokytojo_klientas.post(f"/mokiniai/{kitas_mokinys.id}/redaguoti",
                                      data={**MOKINIO_FORMA, "klases_id": kita_klase.id}).status_code == 403
        assert mokytojo_klientas.post(f"/mokiniai/{kitas_mokinys.id}/salinti").status_code == 403
        nuotrauka = {"nuotrauka": (io.BytesIO(b"\x89PNG"), "nuotrauka.png")}
        assert mokytojo_klientas.post(f"/mokiniai/{kitas_mokinys.id}/nuotrauka", data=nuotrauka,
                                      content_type="multipart/form-data").status_code == 403
        assert db.session.get(Mokinys, kitas_mokinys.id).vardas == "Kitas"

    def test_kitos_klases_mokini_mato_be_mygtuku(self, mokytojo_klientas, kitas_mokinys, vaikas):
        html = mokytojo_klientas.get(f"/mokiniai/{kitas_mokinys.id}").get_data(as_text=True)
        assert "Kitas Mokinys" in html
        assert f"/mokiniai/{kitas_mokinys.id}/redaguoti" not in html
        assert "Mokinio duomenis keičia klasės vadovas (Rasa Vadovė)" in html
        sarasas = mokytojo_klientas.get("/mokiniai/").get_data(as_text=True)
        assert f"/mokiniai/{vaikas.id}/redaguoti" in sarasas
        assert f"/mokiniai/{kitas_mokinys.id}/redaguoti" not in sarasas

    def test_naujas_mokinys_tik_i_savo_klase(self, mokytojo_klientas, klase, kita_klase):
        forma = mokytojo_klientas.get("/mokiniai/naujas").get_data(as_text=True)
        assert set(re.findall(r'<option value="(\d+)"', forma)) == {str(klase.id)}

        html = mokytojo_klientas.post("/mokiniai/naujas",
                                      data={**MOKINIO_FORMA, "klases_id": kita_klase.id}).get_data(as_text=True)
        assert "tik į savo klasę" in html
        assert Mokinys.query.filter_by(vardas="Naujas").count() == 0

        mokytojo_klientas.post("/mokiniai/naujas", data={**MOKINIO_FORMA, "klases_id": klase.id})
        assert Mokinys.query.filter_by(vardas="Naujas").one().klases_id == klase.id

    def test_perkelti_i_kita_klase_negali(self, mokytojo_klientas, vaikas, klase, kita_klase):
        html = mokytojo_klientas.post(f"/mokiniai/{vaikas.id}/redaguoti",
                                      data={**MOKINIO_FORMA, "klases_id": kita_klase.id}).get_data(as_text=True)
        assert "tik savo klasei" in html
        assert db.session.get(Mokinys, vaikas.id).klases_id == klase.id

    def test_grupinis_salinimas_su_kitos_klases_mokiniu_atmetamas(self, mokytojo_klientas, vaikas, kitas_mokinys):
        html = mokytojo_klientas.post("/mokiniai/grupinis-veiksmas",
                                      data={"veiksmas": "salinti", "mokiniu_ids": [vaikas.id, kitas_mokinys.id]},
                                      follow_redirects=True).get_data(as_text=True)
        assert "Galite šalinti tik savo klasės mokinius" in html
        assert Mokinys.query.count() == 2

    def test_mokytojas_be_klases_kurti_negali(self, client, mokytojas, kita_klase):
        client.post("/login", data={"email": mokytojas.email, "slaptazodis": "mokytojas123"})
        html = client.get("/mokiniai/naujas", follow_redirects=True).get_data(as_text=True)
        assert "Mokinius į klasę įtraukia klasės vadovas arba administratorius" in html
        assert 'href="/mokiniai/naujas"' not in client.get("/mokiniai/").get_data(as_text=True)


class TestAdministratorius:
    def test_tvarko_visus_mokinius(self, prisijunges_admin, kitas_mokinys, kita_klase):
        atsakymas = prisijunges_admin.post(f"/mokiniai/{kitas_mokinys.id}/redaguoti",
                                           data={**MOKINIO_FORMA, "klases_id": kita_klase.id})
        assert atsakymas.status_code == 302
        assert prisijunges_admin.post(f"/mokiniai/{kitas_mokinys.id}/salinti").status_code == 302
        assert Mokinys.query.count() == 0
