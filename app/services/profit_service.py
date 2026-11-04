import logging
from pathlib import Path

import numpy as np
import pandas as pd

from app import models
from app.services.price_prediction import get_price_intervals, predict_product_price
from app.services.fuel_service import predict_fuel_price
from app.services.fertilizer_service import get_commodity_price
from app.services.risk import hedef_yil_belirle, sezon_cevir
from app.services.product_catalog import GUBRE_RECETESI, MAZOT_TUKETIMI_LITRE_DONUM, varsayimlar_al

logger = logging.getLogger(__name__)

# Bu dosyanin bulundugu yerden proje kokune cikip data klasorune iniyoruz
KOK_DIZIN = Path(__file__).resolve().parent.parent.parent
URETIM_TAHMIN_PATH = KOK_DIZIN / "data" / "processed" / "data_files" / "üretim_miktari_sonuclari.csv"

# Urun bazli sabitler (gubre recetesi vb.) product_catalog.py'de tutulur.

# Saf maddeyi gercek gubre urunune cevirmek icin carpanlar (PDF'ten)
# Ornek: 14 kg saf azot lazimsa, Ure gubresi olarak 14 x 2.2 = 30.8 kg Ure almamiz lazim
UREYE_CEVIRME_CARPANI = 2.2
DAP_A_CEVIRME_CARPANI = 2.2


def uretim_tahmin_haritasi_olustur():
    df = pd.read_csv(URETIM_TAHMIN_PATH)

    harita = {}
    for i in range(len(df)):
        ilce = df.loc[i, "district"]
        urun = df.loc[i, "product_name"]
        tahmini_uretim = df.loc[i, "2026 Üretim Miktari"]
        harita[(ilce, urun)] = tahmini_uretim
    return harita

# Uygulama baslarken bir kez olusturulur
URETIM_TAHMIN_HARITASI = uretim_tahmin_haritasi_olustur()

#verim orani = tahmini uretim / tahmini ekilen
def verim_orani_hesapla(ilce_id, urun_id, ilce_adi, urun_adi_csv, db):
    kota_kaydi = db.query(models.Kota).filter(
        models.Kota.ilce_id == ilce_id,
        models.Kota.urun_id == urun_id
    ).first()

    if kota_kaydi is None or kota_kaydi.maksimum_kota is None or kota_kaydi.maksimum_kota <= 0: #db kontrlü
        raise ValueError("Bu ilce/urun icin tahmini ekilen alan verisi bulunamadi.")

    anahtar = (ilce_adi, urun_adi_csv)
    tahmini_uretim = URETIM_TAHMIN_HARITASI.get(anahtar)
    logger.debug("verim: anahtar=%s tahmini_uretim=%s maksimum_kota=%s",
                 anahtar, tahmini_uretim, kota_kaydi.maksimum_kota)

    if tahmini_uretim is None or tahmini_uretim <= 0:
        raise ValueError("Bu ilce/urun icin tahmini uretim verisi bulunamadi.")

    verim_orani = tahmini_uretim / kota_kaydi.maksimum_kota
    return verim_orani


def tahmini_gelir_hesapla(donum, verim_orani, tahmini_fiyat):
    tahmini_uretim = donum * verim_orani #kullanıcıdan alınan
    tahmini_gelir = tahmini_uretim * 1000 * tahmini_fiyat #tahmini fiyat modelden gelen kg->ton dönüşümü

    return {
        "tahmini_uretim": round(tahmini_uretim, 2),
        "tahmini_gelir": round(tahmini_gelir, 2),
    }


def gubre_gideri_hesapla(urun, donum, gubre_fiyati_ton_basi):
    recete = GUBRE_RECETESI.get(urun)
    if recete is None:
        raise ValueError(f"{urun} icin gubre recetesi tanimli degil.")

    #ürün için gerekli olan saf azotu bulma
    saf_azot_kg = recete["azot_kg"] * donum
    saf_fosfor_kg = recete["fosfor_kg"] * donum

    #gerekli olan saf azot ve fosfora ulaşmak için gerekli olan üre miktarı ve dap miktarını bulma
    ure_miktari_kg = saf_azot_kg * UREYE_CEVIRME_CARPANI
    dap_miktari_kg = saf_fosfor_kg * DAP_A_CEVIRME_CARPANI

    toplam_gubre_kg = ure_miktari_kg + dap_miktari_kg

    # 3. adim: kg'i tona cevir (fiyat ton bazinda oldugu icin)
    toplam_gubre_ton = toplam_gubre_kg / 1000

    # 4. adim: ton miktarini fiyatla carp, TL gideri bul
    gubre_gideri = toplam_gubre_ton * gubre_fiyati_ton_basi

    return round(gubre_gideri, 2)


def mazot_gideri_hesapla(urun, donum, mazot_fiyati_litre_basi):
    tuketim_litre_donum = MAZOT_TUKETIMI_LITRE_DONUM.get(urun)
    if tuketim_litre_donum is None:
        raise ValueError(f"{urun} icin mazot tuketim verisi tanimli degil.")

    toplam_litre = tuketim_litre_donum * donum
    mazot_gideri = toplam_litre * mazot_fiyati_litre_basi

    return round(mazot_gideri, 2)


def tahmini_gider_hesapla(urun, donum, gubre_fiyati_ton_basi, mazot_fiyati_litre_basi,
                           sulama_maliyeti, iscilik_maliyeti, tohum_maliyeti, donum_basi_ek_maliyet=0):
    gubre_gideri = gubre_gideri_hesapla(urun, donum, gubre_fiyati_ton_basi)
    mazot_gideri = mazot_gideri_hesapla(urun, donum, mazot_fiyati_litre_basi)

    # opsiyonel maliyetleri toplama
    ek_giderler = 0
    if sulama_maliyeti:
        ek_giderler = ek_giderler + sulama_maliyeti
    if iscilik_maliyeti:
        ek_giderler = ek_giderler + iscilik_maliyeti
    if tohum_maliyeti:
        ek_giderler = ek_giderler + tohum_maliyeti
    # plan onerisinde ciftcinin girdigi donum basi diger giderler (iscilik, tohum, sulama, kira...)
    if donum_basi_ek_maliyet:
        ek_giderler = ek_giderler + donum_basi_ek_maliyet * donum

    toplam_gider = gubre_gideri + mazot_gideri + ek_giderler

    return {
        "gubre_gideri": gubre_gideri,
        "mazot_gideri": mazot_gideri,
        "ek_giderler": round(ek_giderler, 2),
        "toplam_gider": round(toplam_gider, 2),
    }


def net_kar_hesapla(tahmini_gelir, toplam_gider):
    return round(float(tahmini_gelir - toplam_gider), 2)

# Ciftcinin kendi gecmis verimi n yillik ise agirligi n / (n + KREDIBILITE_K) olur (kredibilite
# agirliklandirmasi): tek yillik beyan ilce ortalamasini 1/3 oraninda, bes yillik kayit 5/7
# oraninda etkiler. Boylece tek bir iyi ya da kotu yil plani tek basina belirlemez.
KREDIBILITE_K = 2


def verim_birlestir(ilce_verimi, gecmis_verimler=None):
    if not gecmis_verimler:
        return {
            "verim": ilce_verimi,
            "ilce_verimi": ilce_verimi,
            "kendi_verim_ortalamasi": None,
            "kendi_verim_agirligi": 0.0,
        }

    n = len(gecmis_verimler)
    agirlik = n / (n + KREDIBILITE_K)
    ortalama = sum(gecmis_verimler) / n
    return {
        "verim": agirlik * ortalama + (1 - agirlik) * ilce_verimi,
        "ilce_verimi": ilce_verimi,
        "kendi_verim_ortalamasi": ortalama,
        "kendi_verim_agirligi": agirlik,
    }


def basabas_fiyati_hesapla(toplam_gider, tahmini_uretim_ton):
    """Giderleri tam karsilayan satis fiyati (TL/kg)."""
    if tahmini_uretim_ton <= 0:
        return None
    return toplam_gider / (tahmini_uretim_ton * 1000)


def zarar_olasiligi_hesapla(tahmini_fiyat, basabas_fiyati, log_hatalar):
    """Modelin gecmis tahmin hatalari bugune uygulandiginda fiyatin basabasin altinda kalma orani.
    Yalnizca fiyat belirsizligini kapsar; verim ve gider sabit kabul edilir."""
    if not log_hatalar or basabas_fiyati is None:
        return None
    olasi_fiyatlar = tahmini_fiyat * np.exp(np.asarray(log_hatalar, dtype=float))
    return round(float(np.mean(olasi_fiyatlar < basabas_fiyati)), 3)


#fiyat tahmini modelini cagırıyor
def fiyat_tahmini_al(urun_adi_csv, hedef_sezon):
    return predict_product_price(product_name=urun_adi_csv, target_season=hedef_sezon)


def tahmini_fiyat_al(urun_adi_csv, hedef_yil, hedef_sezon):
    return fiyat_tahmini_al(urun_adi_csv, hedef_sezon)["predicted_price"]


def guncel_gubre_fiyati_al():
    return get_commodity_price("urea")

#mazot tahmin modelini cagırıyor
def tahmini_mazot_fiyati_al(hedef_yil, hedef_sezon):
    return predict_fuel_price(hedef_yil, hedef_sezon)


def kar_hesapla_tam(db, ilce_id, urun_id, ilce_adi, urun_sistem_adi, urun_adi_csv,
                     donum, hedef_yil, hedef_sezon,
                     sulama_maliyeti, iscilik_maliyeti, tohum_maliyeti,
                     gecmis_verimler=None, donum_basi_ek_maliyet=0):
    # 1. adim: verim (ilce ortalamasi, varsa ciftcinin kendi gecmisiyle birlestirilir)
    ilce_verimi = verim_orani_hesapla(ilce_id, urun_id, ilce_adi, urun_adi_csv, db)
    verim = verim_birlestir(ilce_verimi, gecmis_verimler)

    # 2. adim: tahmini fiyat ve belirsizlik araligi
    fiyat = fiyat_tahmini_al(urun_adi_csv, hedef_sezon)
    tahmini_fiyat = fiyat["predicted_price"]

    # 3. adim: gelir hesapla
    gelir_sonucu = tahmini_gelir_hesapla(donum, verim["verim"], tahmini_fiyat)

    # 4. adim: gubre ve mazot fiyatlarini al
    gubre_fiyati_ton_basi = guncel_gubre_fiyati_al()
    mazot_fiyati_litre_basi = tahmini_mazot_fiyati_al(hedef_yil, hedef_sezon)

    # 5. adim: gider hesapla
    gider_sonucu = tahmini_gider_hesapla(
        urun_sistem_adi, donum, gubre_fiyati_ton_basi, mazot_fiyati_litre_basi,
        sulama_maliyeti, iscilik_maliyeti, tohum_maliyeti, donum_basi_ek_maliyet
    )
    toplam_gider = gider_sonucu["toplam_gider"]

    # 6. adim: net kar, kotu/iyi senaryo, basabas ve zarar olasiligi
    net_kar = net_kar_hesapla(gelir_sonucu["tahmini_gelir"], toplam_gider)
    uretim_ton = donum * verim["verim"]

    def senaryo_kari(senaryo_fiyati):
        if senaryo_fiyati is None:
            return None
        return round(float(uretim_ton * 1000 * senaryo_fiyati - toplam_gider), 2)

    basabas = basabas_fiyati_hesapla(toplam_gider, uretim_ton)
    araliklar = get_price_intervals()

    logger.debug(
        "kar hesabi: ilce=%s urun=%s donum=%s verim=%s fiyat=%s uretim=%s gelir=%s gubre=%s mazot=%s ek=%s gider=%s",
        ilce_adi, urun_adi_csv, donum, verim["verim"], tahmini_fiyat,
        gelir_sonucu["tahmini_uretim"], gelir_sonucu["tahmini_gelir"],
        gider_sonucu["gubre_gideri"], gider_sonucu["mazot_gideri"],
        gider_sonucu["ek_giderler"], toplam_gider,
    )

    return {
        "tahmini_uretim": gelir_sonucu["tahmini_uretim"],
        "tahmini_fiyat": tahmini_fiyat,
        "tahmini_gelir": gelir_sonucu["tahmini_gelir"],
        "gubre_gideri": gider_sonucu["gubre_gideri"],
        "mazot_gideri": gider_sonucu["mazot_gideri"],
        "ek_giderler": gider_sonucu["ek_giderler"],
        "toplam_gider": toplam_gider,
        "net_kar": net_kar,
        # belirsizlik
        "fiyat_dusuk": fiyat["price_low"],
        "fiyat_yuksek": fiyat["price_high"],
        "net_kar_dusuk": senaryo_kari(fiyat["price_low"]),
        "net_kar_yuksek": senaryo_kari(fiyat["price_high"]),
        "aralik_isabeti": None if araliklar is None else araliklar["loo_coverage"],
        "basabas_fiyati": None if basabas is None else round(float(basabas), 2),
        "zarar_olasiligi": zarar_olasiligi_hesapla(tahmini_fiyat, basabas, fiyat["log_errors"]),
        # verim kaynagi
        "verim_ton_donum": round(float(verim["verim"]), 3),
        "ilce_verimi_ton_donum": round(float(verim["ilce_verimi"]), 3),
        "kendi_verim_agirligi": round(verim["kendi_verim_agirligi"], 2),
        # iscilik/tohum/sulama girilmediyse zarar olasiligi oldugundan dusuk gorunur
        "maliyetler_eksik": not (sulama_maliyeti or iscilik_maliyeti or tohum_maliyeti or donum_basi_ek_maliyet),
        "varsayimlar": varsayimlar_al(urun_sistem_adi),
    }

def kar_hesaplama_son(db,ilce,urun,sezon,donum,sulama_maliyeti=0,iscilik_maliyeti=0,tohum_maliyeti=0,
                      gecmis_verimler=None, donum_basi_ek_maliyet=0):
    ilce_kaydi = db.query(models.Ilce).filter(
        models.Ilce.ilce_adi == ilce
    ).first()

    urun_kaydi = db.query(models.Urun).filter(
        models.Urun.urun_adi == urun
    ).first()

    if not ilce_kaydi or not urun_kaydi:
        raise ValueError("İlçe veya ürün bulunamadı.")

    hedef_yil = hedef_yil_belirle(sezon)
    hedef_sezon = sezon_cevir(sezon)

    return kar_hesapla_tam(
        db=db,
        ilce_id=ilce_kaydi.ilce_id,
        urun_id=urun_kaydi.urun_id,
        ilce_adi=ilce,
        urun_sistem_adi=urun,
        urun_adi_csv=urun,
        donum=donum,
        hedef_yil=hedef_yil,
        hedef_sezon=hedef_sezon,
        sulama_maliyeti=sulama_maliyeti,
        iscilik_maliyeti=iscilik_maliyeti,
        tohum_maliyeti=tohum_maliyeti,
        gecmis_verimler=gecmis_verimler,
        donum_basi_ek_maliyet=donum_basi_ek_maliyet,
    )
