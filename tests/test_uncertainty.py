import math

import pandas as pd
import pytest
from pydantic import ValidationError

from app.schemas import KarHesabiRequest, OptimizationManuelRequest
from app.services import price_prediction
from app.services.inflation_service import blend_with_naive
from app.services.optimization_plan import add_final_score, drop_unprofitable
from app.services.product_catalog import varsayim_ozeti, varsayimlar_al
from app.services.profit_service import (
    KREDIBILITE_K,
    basabas_fiyati_hesapla,
    verim_birlestir,
    zarar_olasiligi_hesapla,
)


# ---------- ciftcinin kendi verimi ----------

def test_gecmis_verim_yoksa_ilce_verimi_kullanilir():
    sonuc = verim_birlestir(4.0, None)
    assert sonuc["verim"] == 4.0
    assert sonuc["kendi_verim_agirligi"] == 0.0


def test_kredibilite_agirligi_yil_sayisiyla_artar():
    bir_yil = verim_birlestir(4.0, [7.0])
    bes_yil = verim_birlestir(4.0, [7.0] * 5)
    assert bir_yil["kendi_verim_agirligi"] == pytest.approx(1 / (1 + KREDIBILITE_K))
    assert bes_yil["kendi_verim_agirligi"] == pytest.approx(5 / (5 + KREDIBILITE_K))
    # tek bir yil ilce degerini ancak kismen kaydirir
    assert 4.0 < bir_yil["verim"] < bes_yil["verim"] < 7.0


def test_mantiksiz_verim_reddedilir():
    temel = {"ilce": "Tire", "urun": "KARPUZ", "donum": 10, "sezon": "Yaz"}
    with pytest.raises(ValidationError):
        KarHesabiRequest(**temel, gecmis_verimler=[300])
    with pytest.raises(ValidationError):
        KarHesabiRequest(**temel, gecmis_verimler=[-1])
    assert KarHesabiRequest(**temel, gecmis_verimler=[5.5, 6]).gecmis_verimler == [5.5, 6]


# ---------- basabas ve zarar olasiligi ----------

def test_basabas_fiyati():
    # 10 ton uretim, 50.000 TL gider -> 5 TL/kg
    assert basabas_fiyati_hesapla(50_000, 10) == pytest.approx(5.0)
    assert basabas_fiyati_hesapla(50_000, 0) is None


def test_zarar_olasiligi_gecmis_hatalardan_hesaplanir():
    # tahmin 10 TL; gecmiste gercek fiyat tahminin %50'si, %100'u, %150'si, %200'u cikmis
    hatalar = [math.log(0.5), 0.0, math.log(1.5), math.log(2.0)]
    assert zarar_olasiligi_hesapla(10, 8, hatalar) == pytest.approx(0.25)
    assert zarar_olasiligi_hesapla(10, 1, hatalar) == 0.0
    assert zarar_olasiligi_hesapla(10, 8, None) is None


# ---------- fiyat araligi ----------

def test_fiyat_tahmini_araligi_tahmini_kapsar():
    if price_prediction.get_price_intervals() is None:
        pytest.skip("models/price_intervals.json yok: python -m app.scripts.price_intervals")
    sonuc = price_prediction.predict_product_price("DOMATES SALKIM", "Spring")
    assert sonuc["price_low"] < sonuc["predicted_price"] < sonuc["price_high"]
    assert sonuc["log_errors"]


def test_aralik_dosyasi_olculen_kapsamayi_icerir():
    araliklar = price_prediction.get_price_intervals()
    if araliklar is None:
        pytest.skip("models/price_intervals.json yok")
    assert 0 < araliklar["loo_coverage"] <= 1
    assert set(araliklar["by_horizon"]) == {"1", "2", "3", "4"}


def test_ufuk_1_4_araligina_sinirlanir():
    if price_prediction.get_price_intervals() is None:
        pytest.skip("models/price_intervals.json yok")
    assert price_prediction.interval_for_horizon(0) == price_prediction.interval_for_horizon(1)
    assert price_prediction.interval_for_horizon(9) == price_prediction.interval_for_horizon(4)


# ---------- enflasyon karmasi ----------

def test_enflasyon_karmasi():
    assert blend_with_naive(20.0, 30.0, 0.5) == pytest.approx(25.0)
    assert blend_with_naive(20.0, 30.0, 0.0) == pytest.approx(20.0)


# ---------- temkinli strateji ----------

def _iki_urun():
    # A: beklenen kar yuksek ama kotu senaryoda zarar; B: daha az kar, kotu senaryoda bile karli
    return pd.DataFrame(
        {
            "product_name": ["A", "B"],
            "profit_per_decare": [10_000.0, 6_000.0],
            "profit_low_per_decare": [-4_000.0, 2_000.0],
            "risk_score": [40.0, 40.0],
        }
    )


def test_dengeli_strateji_beklenen_kari_odullendirir():
    sonuc = add_final_score(_iki_urun(), strateji="dengeli").set_index("product_name")
    assert sonuc.loc["A", "final_score"] > sonuc.loc["B", "final_score"]


def test_temkinli_strateji_kotu_senaryoyu_odullendirir():
    sonuc = add_final_score(_iki_urun(), strateji="temkinli").set_index("product_name")
    assert sonuc.loc["B", "final_score"] > sonuc.loc["A", "final_score"]


def test_gecersiz_strateji_reddedilir():
    with pytest.raises(ValueError):
        add_final_score(_iki_urun(), strateji="agresif")
    with pytest.raises(ValidationError):
        OptimizationManuelRequest(ilce_adi="Tire", donum=10, sezon="Yaz", strateji="agresif")


# ---------- varsayim seffafligi ----------

def test_olculmemis_mazot_degeri_isaretlenir():
    assert not any("Mazot" in n for n in varsayimlar_al("DOMATES SALKIM"))
    assert any("Mazot" in n for n in varsayimlar_al("KARPUZ"))


def test_varsayim_ozeti_tum_urunleri_listeler():
    ozet = varsayim_ozeti()
    assert {satir["urun"] for satir in ozet} >= {"DOMATES SALKIM", "MARUL"}
    assert all("mazot_kaynagi" in satir for satir in ozet)


def test_zarar_eden_urune_alan_ayrilmaz():
    data = _iki_urun()
    data.loc[0, "profit_per_decare"] = -500.0
    assert drop_unprofitable(data)["product_name"].tolist() == ["B"]


def test_urune_ozel_aralik_urunler_arasinda_farklidir():
    if price_prediction.get_price_intervals() is None:
        pytest.skip("models/price_intervals.json yok")
    genislik = {
        urun: price_prediction.interval_for(urun, 2)["q_high"] - price_prediction.interval_for(urun, 2)["q_low"]
        for urun in ["DOMATES SALKIM", "KARPUZ", "BROKOLI", "ISPANAK"]
    }
    assert len({round(g, 3) for g in genislik.values()}) > 1


def test_bilinmeyen_urun_ufuk_araligina_duser():
    if price_prediction.get_price_intervals() is None:
        pytest.skip("models/price_intervals.json yok")
    assert price_prediction.interval_for("YOK", 2) == price_prediction.interval_for_horizon(2)
