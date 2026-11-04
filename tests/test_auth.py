from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app import auth, models
from app.database import SessionLocal
from app.main import app_tarim
from app.routes import get_password_hash


@pytest.fixture(scope="module")
def client():
    with TestClient(app_tarim) as c:
        yield c


@pytest.fixture(scope="module")
def kullanicilar():
    db = SessionLocal()
    try:
        ilce = models.Ilce(ilce_adi="TestIlce")
        a = models.Kullanici(ad_soyad="Ayse", email="a@test.com", sifre_hash=get_password_hash("sifre123"))
        b = models.Kullanici(ad_soyad="Burak", email="b@test.com", sifre_hash=get_password_hash("sifre123"))
        yonetici = models.Kullanici(
            ad_soyad="Yonetici", email="y@test.com", sifre_hash=get_password_hash("sifre123"), is_admin=True
        )
        db.add_all([ilce, a, b, yonetici])
        db.commit()
        tarla = models.Tarla(kullanici_id=a.kullanici_id, tarla_adi="A tarlasi", ilce_id=ilce.ilce_id)
        db.add(tarla)
        db.commit()
        return {"a": a.kullanici_id, "b": b.kullanici_id, "admin": yonetici.kullanici_id, "tarla": tarla.tarla_id}
    finally:
        db.close()


def giris(client, email):
    r = client.post("/kullanici/giris", json={"email": email, "sifre": "sifre123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_giris_token_doner(client, kullanicilar):
    r = client.post("/kullanici/giris", json={"email": "a@test.com", "sifre": "sifre123"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert auth.token_coz(r.json()["access_token"]) == kullanicilar["a"]


def test_yanlis_sifre_reddedilir(client, kullanicilar):
    r = client.post("/kullanici/giris", json={"email": "a@test.com", "sifre": "yanlis"})
    assert r.status_code == 401


@pytest.mark.parametrize("yol", ["/tarla/liste", "/risk/gecmis", "/admin/kullanicilar", "/admin/urunler"])
def test_token_olmadan_401(client, kullanicilar, yol):
    assert client.get(yol).status_code == 401


def test_bozuk_ve_suresi_dolmus_token_reddedilir(client, kullanicilar):
    assert client.get("/tarla/liste", headers={"Authorization": "Bearer bozuk"}).status_code == 401

    gecmis = datetime.now(timezone.utc) - timedelta(hours=1)
    eski = jwt.encode(
        {"sub": str(kullanicilar["a"]), "iat": gecmis - timedelta(hours=1), "exp": gecmis},
        auth._secret_al(),
        algorithm=auth.ALGORITHM,
    )
    assert client.get("/tarla/liste", headers={"Authorization": f"Bearer {eski}"}).status_code == 401


def test_baskasinin_kimligiyle_islem_yapilamaz(client, kullanicilar):
    h_b = giris(client, "b@test.com")
    # B, A'nin tarlasini goremez ve silemez
    assert client.get("/tarla/liste", headers=h_b).json() == []
    assert client.delete(f"/tarla/sil/{kullanicilar['tarla']}", headers=h_b).status_code == 404
    # B, A'nin bilgilerini okuyamaz
    assert client.get(f"/kullanici/{kullanicilar['a']}", headers=h_b).status_code == 403
    assert client.get(f"/urunlerim/{kullanicilar['a']}", headers=h_b).status_code == 403
    # Govdede baskasinin kullanici_id'si gonderilse bile token'daki kimlik gecerli
    r = client.get("/tarla/liste", params={"kullanici_id": kullanicilar["a"]}, headers=h_b)
    assert r.json() == []


def test_sahibi_kendi_tarlasini_gorur(client, kullanicilar):
    h_a = giris(client, "a@test.com")
    liste = client.get("/tarla/liste", headers=h_a).json()
    assert [t["tarla_id"] for t in liste] == [kullanicilar["tarla"]]


def test_admin_uc_noktalari_yalnizca_admine_aciktir(client, kullanicilar):
    assert client.get("/admin/kullanicilar", headers=giris(client, "a@test.com")).status_code == 403
    # Eski sizdirma: admin_id sorgu parametresi artik hicbir yetki vermez
    r = client.get("/admin/kullanicilar", params={"admin_id": kullanicilar["admin"]}, headers=giris(client, "a@test.com"))
    assert r.status_code == 403
    assert client.get("/admin/kullanicilar", headers=giris(client, "y@test.com")).status_code == 200


def test_herkese_acik_uc_noktalar_token_istemez(client, kullanicilar):
    assert client.get("/ilce/liste").status_code == 200
    assert client.get("/urun/liste").status_code == 200
