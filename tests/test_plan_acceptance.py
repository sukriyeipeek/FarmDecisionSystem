import math
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app.routes import oneri_onayla
from app.schemas import OnerıOnaylaRequest as OneriOnaylaRequest


@pytest.fixture
def acceptance_db():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    db = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)()
    user = models.Kullanici(ad_soyad="Test", email=f"acceptance-{uuid.uuid4()}@example.com", sifre_hash="x")
    district = models.Ilce(ilce_adi=f"Test İlçe {uuid.uuid4()}")
    db.add_all([user, district])
    db.flush()
    field = models.Tarla(kullanici_id=user.kullanici_id, tarla_adi="Tarla", ilce_id=district.ilce_id)
    empty = models.Urun(urun_adi="Boş", aktif=True)
    product = models.Urun(urun_adi="DOMATES SALKIM", aktif=True)
    inactive = models.Urun(urun_adi="PASİF", aktif=False)
    db.add_all([field, empty, product, inactive])
    db.flush()
    db.add(models.TarlaUrun(tarla_id=field.tarla_id, urun_id=empty.urun_id, donum=10))
    db.add(models.Kota(urun_id=product.urun_id, ilce_id=district.ilce_id, maksimum_kota=20, kullanilan_kota=0))
    db.commit()
    yield db, user, field, product, inactive
    db.close()
    test_engine.dispose()


def test_acceptance_rejects_over_allocation_without_partial_write(acceptance_db):
    db, user, field, product, _ = acceptance_db
    payload = OneriOnaylaRequest(
        tarla_id=field.tarla_id,
        hesaplanan_toplam_kar=100,
        urunler=[{"urun_adi": product.urun_adi, "donum": 11}],
    )

    with pytest.raises(HTTPException) as error:
        oneri_onayla(payload, db, user)
    assert error.value.status_code == 409

    db.expire_all()
    empty = db.query(models.TarlaUrun).filter_by(tarla_id=field.tarla_id, urun_id=product.urun_id).first()
    assert empty is None
    remaining = db.query(models.TarlaUrun).filter_by(tarla_id=field.tarla_id).first()
    assert remaining.donum == 10
    assert db.query(models.OneriPaketi).count() == 0


def test_acceptance_rejects_duplicate_and_inactive_products(acceptance_db):
    db, user, field, product, inactive = acceptance_db
    duplicate = OneriOnaylaRequest(
        tarla_id=field.tarla_id,
        hesaplanan_toplam_kar=100,
        urunler=[
            {"urun_adi": product.urun_adi, "donum": 1},
            {"urun_adi": product.urun_adi, "donum": 1},
        ],
    )
    with pytest.raises(HTTPException) as error:
        oneri_onayla(duplicate, db, user)
    assert error.value.status_code == 400

    inactive_payload = OneriOnaylaRequest(
        tarla_id=field.tarla_id,
        hesaplanan_toplam_kar=100,
        urunler=[{"urun_adi": inactive.urun_adi, "donum": 1}],
    )
    with pytest.raises(HTTPException) as error:
        oneri_onayla(inactive_payload, db, user)
    assert error.value.status_code == 400
    assert db.query(models.OneriPaketi).count() == 0


def test_acceptance_commits_area_quota_and_ekim_record_atomically(acceptance_db):
    db, user, field, product, _ = acceptance_db
    payload = OneriOnaylaRequest(
        tarla_id=field.tarla_id,
        hesaplanan_toplam_kar=100,
        urunler=[{"urun_adi": product.urun_adi, "donum": 2}],
    )
    result = oneri_onayla(payload, db, user)

    assert result["paket_id"]
    assert db.query(models.TarlaUrun).filter_by(tarla_id=field.tarla_id, urun_id=product.urun_id).one().donum == 2
    empty = db.query(models.Urun).filter_by(urun_adi="Boş").one()
    assert db.query(models.TarlaUrun).filter_by(tarla_id=field.tarla_id, urun_id=empty.urun_id).one().donum == 8
    assert db.query(models.EkimKaydi).one().ekilen_donum == 2
    assert db.query(models.Kota).filter_by(urun_id=product.urun_id).one().kullanilan_kota == 2


def test_acceptance_flush_failure_rolls_back_everything(acceptance_db, monkeypatch):
    db, user, field, product, _ = acceptance_db
    payload = OneriOnaylaRequest(
        tarla_id=field.tarla_id,
        hesaplanan_toplam_kar=100,
        urunler=[{"urun_adi": product.urun_adi, "donum": 2}],
    )
    original_flush = db.flush
    calls = {"count": 0}

    def fail_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("injected flush failure")
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db, "flush", fail_once)
    with pytest.raises(HTTPException) as error:
        oneri_onayla(payload, db, user)
    assert error.value.status_code == 500
    assert db.query(models.OneriPaketi).count() == 0
    assert db.query(models.EkimKaydi).count() == 0
    assert db.query(models.TarlaUrun).filter_by(tarla_id=field.tarla_id, urun_id=product.urun_id).one_or_none() is None


def test_acceptance_rejects_other_owner(acceptance_db):
    db, _, field, product, _ = acceptance_db
    other = models.Kullanici(ad_soyad="Other", email=f"other-{uuid.uuid4()}@example.com", sifre_hash="x")
    db.add(other)
    db.commit()
    payload = OneriOnaylaRequest(
        tarla_id=field.tarla_id,
        hesaplanan_toplam_kar=100,
        urunler=[{"urun_adi": product.urun_adi, "donum": 1}],
    )
    with pytest.raises(HTTPException) as error:
        oneri_onayla(payload, db, other)
    assert error.value.status_code == 404


def test_acceptance_schema_rejects_non_finite_and_non_positive_values():
    with pytest.raises(ValueError):
        OneriOnaylaRequest(tarla_id=1, hesaplanan_toplam_kar=math.inf, urunler=[])
    with pytest.raises(ValueError):
        OneriOnaylaRequest(
            tarla_id=1,
            hesaplanan_toplam_kar=1,
            urunler=[{"urun_adi": "DOMATES SALKIM", "donum": 0}],
        )
