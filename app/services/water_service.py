"""Approximate seasonal planning demand; not a local ET or irrigation measurement.

1 mm over 1 decare (1000 m2) = 1 m3. Ranges describe a whole crop cycle,
not one calendar quarter. Missing crop-specific data uses an explicit proxy.
"""

from app.services.product_catalog import URUNLER

FAO_CROPS = "https://www.fao.org/4/s2022e/s2022e02.htm"
TAMU_CROPS = "https://aggie-horticulture.tamu.edu/vegetable/guides/texas-vegetable-growers-handbook/appendix/tables-commercial-vegetable-growers-handbook/"
FAO_EFFICIENCY = "https://www.fao.org/4/t7202e/t7202e08.htm"
IRRIGATION_EFFICIENCY = {"damla": 0.90, "yagmurlama": 0.75, "salma": 0.60}

# low/high mm per entire growing period, source, proxy (if any).
WATER_PROFILES = {
    "DOMATES SALKIM": (400, 800, FAO_CROPS, None),
    "BIBER SIVRI": (600, 900, FAO_CROPS, None),
    "SALATALIK SILOR": (508, 635, TAMU_CROPS, "Sofralık salatalık"),
    "KABAK TAZE": (635, 762, TAMU_CROPS, "Balkabağı; taze kabak için yaklaşık vekil"),
    "PATLICAN UZUN": (508, 889, TAMU_CROPS, None),
    "SOGAN KURU": (350, 550, FAO_CROPS, None),
    "KARPUZ": (254, 381, TAMU_CROPS, None),
    "BAKLA": (300, 500, FAO_CROPS, "Fasulye; bakla için yaklaşık vekil"),
    "BEZELYE": (350, 500, FAO_CROPS, None),
    "BROKOLI": (508, 635, TAMU_CROPS, None),
    "ISPANAK": (254, 381, TAMU_CROPS, None),
    "KARNABAHAR": (508, 635, TAMU_CROPS, None),
    "LAHANA BEYAZ": (350, 500, FAO_CROPS, None),
    "LAHANA KIRMIZI": (350, 500, FAO_CROPS, "Lahana; renk/çeşit ayrımı yok"),
    "MARUL": (203.2, 304.8, TAMU_CROPS, None),
    "PIRASA": (350, 550, FAO_CROPS, "Soğan; pırasa için yaklaşık vekil"),
}


def estimate_water(product_name, season, irrigation_method="damla"):
    if product_name not in WATER_PROFILES:
        raise ValueError(f"Su profili bulunamadı: {product_name}")
    if season not in ("Spring", "Summer", "Fall", "Winter"):
        raise ValueError(f"Geçersiz sezon: {season}")
    if irrigation_method not in IRRIGATION_EFFICIENCY:
        raise ValueError("Geçersiz sulama yöntemi.")
    low, high, source, proxy = WATER_PROFILES[product_name]
    efficiency = IRRIGATION_EFFICIENCY[irrigation_method]
    notes = [
        "Tüm yetiştirme dönemi için literatür aralığının orta değeri kullanıldı; İzmir'de ölçülmedi.",
        "Yerel yağış/toprak verisi yok: etkili yağış sıfır varsayıldı; mevsimler arasında iklim düzeltmesi yapılmadı.",
        "Tarla uygulama verimi yaklaşık değerdir; kaynaktan tarlaya iletim kayıpları dahil değildir.",
    ]
    if proxy:
        notes.append(f"Vekil ürün varsayımı: {proxy}.")
    return {
        "water_m3_per_decare": (low + high) / 2 / efficiency,
        "water_low_m3_per_decare": low / efficiency,
        "water_high_m3_per_decare": high / efficiency,
        "irrigation_efficiency": efficiency,
        "source": source,
        "efficiency_source": FAO_EFFICIENCY,
        "assumptions": notes,
    }


def water_catalog():
    return [
        {"product_name": product, "seasons": info["mevsimler"],
         **estimate_water(product, info["mevsimler"][0])}
        for product, info in URUNLER.items()
    ]
