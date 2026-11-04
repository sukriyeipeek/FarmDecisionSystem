import pandas as pd
import pytest

from app.services.optimization_plan import PRODUCT_SEASONS
from app.services.product_catalog import (
    GUBRE_RECETESI,
    MAZOT_TUKETIMI_LITRE_DONUM,
    URUNLER,
    URUN_MEVSIMLERI,
)
from app.services.profit_service import gubre_gideri_hesapla, mazot_gideri_hesapla

VERI = "data/processed/data_files"
# Bilinen istisna: fiyat veri setinde yok; API de bu urunu listelemiyor (/urun/liste).
VERI_SETINDE_OLMAYAN = {"final_price_dataset.csv": {"SOGAN KURU"}}


def test_tum_sabit_tablolari_ayni_urunleri_icerir():
    adlar = set(URUNLER)
    assert set(GUBRE_RECETESI) == adlar
    assert set(MAZOT_TUKETIMI_LITRE_DONUM) == adlar
    assert set(PRODUCT_SEASONS) == adlar
    assert set(URUN_MEVSIMLERI) == adlar


@pytest.mark.parametrize("dosya", ["final_optimization.csv", "final_price_dataset.csv", "final_risk_dataset.csv"])
def test_katalog_veri_setleriyle_ayni_adlari_kullanir(dosya):
    # Ad uyumsuzlugu (ornegin MARUL / MARUL GOBEKLI) urunun plandan sessizce dusmesine yol acar.
    veri_adlari = set(pd.read_csv(f"{VERI}/{dosya}")["product_name"].unique())
    eksik = set(URUNLER) - veri_adlari - VERI_SETINDE_OLMAYAN.get(dosya, set())
    assert not eksik, f"{dosya} icinde bulunmayan katalog urunleri: {eksik}"


def test_marul_icin_hesaplar_calisir():
    assert "MARUL" in PRODUCT_SEASONS
    assert gubre_gideri_hesapla("MARUL", 1, 1000) > 0
    assert mazot_gideri_hesapla("MARUL", 1, 10) > 0
