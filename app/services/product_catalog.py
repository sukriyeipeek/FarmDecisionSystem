"""Urunlere ait tum sabitler tek yerde.

Urun adlari data/processed/data_files altindaki veri setleri ve veritabanindaki
`urun` tablosuyla birebir ayni olmalidir (bkz. tests/test_product_catalog.py).
Gubre degerleri Tarim ve Orman Bakanligi'nin urun bazli azot/fosfor tavsiyelerine,
mazot tuketimi ise yalnizca domates icin olculen degere dayanir; digerleri yaklasiktir.
"""

# Mazot tuketimi (L/donum): yalnizca domates icin net veri var, digerlerinde ayni deger kullanildi.
VARSAYILAN_MAZOT_L_DONUM = 16.98

_DOMATES_GRUBU_GUBRE = {"azot_kg": 14, "fosfor_kg": 10}
_GENEL_GUBRE = {"azot_kg": 15, "fosfor_kg": 9}

URUNLER = {
    "DOMATES SALKIM":  {"mevsimler": ["Spring"],                   "gubre": _DOMATES_GRUBU_GUBRE},
    "BIBER SIVRI":     {"mevsimler": ["Spring"],                   "gubre": _DOMATES_GRUBU_GUBRE},
    "SALATALIK SILOR": {"mevsimler": ["Spring", "Summer"],         "gubre": _DOMATES_GRUBU_GUBRE},
    "KABAK TAZE":      {"mevsimler": ["Spring", "Summer"],         "gubre": _DOMATES_GRUBU_GUBRE},
    "PATLICAN UZUN":   {"mevsimler": ["Spring"],                   "gubre": _DOMATES_GRUBU_GUBRE},
    "SOGAN KURU":      {"mevsimler": ["Fall", "Spring"],           "gubre": {"azot_kg": 13, "fosfor_kg": 9}},
    "KARPUZ":          {"mevsimler": ["Spring"],                   "gubre": _GENEL_GUBRE},
    "BAKLA":           {"mevsimler": ["Fall", "Winter"],           "gubre": _GENEL_GUBRE},
    "BEZELYE":         {"mevsimler": ["Fall", "Winter"],           "gubre": _GENEL_GUBRE},
    "BROKOLI":         {"mevsimler": ["Summer", "Fall"],           "gubre": _GENEL_GUBRE},
    "ISPANAK":         {"mevsimler": ["Fall", "Winter"],           "gubre": _GENEL_GUBRE},
    "KARNABAHAR":      {"mevsimler": ["Summer", "Fall"],           "gubre": _GENEL_GUBRE},
    "LAHANA BEYAZ":    {"mevsimler": ["Summer", "Fall"],           "gubre": _GENEL_GUBRE},
    "LAHANA KIRMIZI":  {"mevsimler": ["Summer", "Fall"],           "gubre": _GENEL_GUBRE},
    "MARUL":           {"mevsimler": ["Fall", "Winter", "Spring"], "gubre": _GENEL_GUBRE},
    "PIRASA":          {"mevsimler": ["Spring", "Summer"],         "gubre": _GENEL_GUBRE},
}

URUN_MEVSIMLERI = {ad: bilgi["mevsimler"] for ad, bilgi in URUNLER.items()}
GUBRE_RECETESI = {ad: dict(bilgi["gubre"]) for ad, bilgi in URUNLER.items()}
MAZOT_TUKETIMI_LITRE_DONUM = {ad: VARSAYILAN_MAZOT_L_DONUM for ad in URUNLER}
