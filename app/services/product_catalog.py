"""Urunlere ait tum sabitler tek yerde.

Urun adlari data/processed/data_files altindaki veri setleri ve veritabanindaki
`urun` tablosuyla birebir ayni olmalidir (bkz. tests/test_product_catalog.py).
Gubre degerleri Tarim ve Orman Bakanligi'nin urun bazli azot/fosfor tavsiyelerine,
mazot tuketimi ise yalnizca domates icin olculen degere dayanir; digerleri yaklasiktir.
"""

# Mazot tuketimi (L/donum): yalnizca domates icin olculmus deger var. Baska bir urun icin
# kaynakli deger bulundugunda URUNLER'deki kaydina "mazot_l_donum" ve "mazot_kaynagi" ekleyin;
# o urun icin varsayim uyarisi kendiliginden kalkar.
VARSAYILAN_MAZOT_L_DONUM = 16.98
VARSAYILAN_MAZOT_KAYNAGI = "domates icin olculen deger"
GUBRE_KAYNAGI = "Tarim ve Orman Bakanligi azot/fosfor tavsiyesi"

_DOMATES_GRUBU_GUBRE = {"azot_kg": 14, "fosfor_kg": 10}
_GENEL_GUBRE = {"azot_kg": 15, "fosfor_kg": 9}

URUNLER = {
    "DOMATES SALKIM":  {"mevsimler": ["Spring"],                   "gubre": _DOMATES_GRUBU_GUBRE,
                        "mazot_l_donum": VARSAYILAN_MAZOT_L_DONUM, "mazot_kaynagi": VARSAYILAN_MAZOT_KAYNAGI},
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
MAZOT_TUKETIMI_LITRE_DONUM = {
    ad: bilgi.get("mazot_l_donum", VARSAYILAN_MAZOT_L_DONUM) for ad, bilgi in URUNLER.items()
}


def varsayimlar_al(urun: str) -> list[str]:
    """Bu urunun kar hesabinda olculmus veri yerine kullanilan yaklasik degerler."""
    bilgi = URUNLER.get(urun)
    if bilgi is None:
        return []

    notlar = []
    if "mazot_kaynagi" not in bilgi:
        notlar.append(
            f"Mazot tüketimi bu ürün için ölçülmedi; domates değeri "
            f"({VARSAYILAN_MAZOT_L_DONUM} L/dönüm) kullanıldı."
        )
    notlar.append("İşçilik, tohum ve sulama girilmediyse giderlere dahil değildir.")
    return notlar


def varsayim_ozeti() -> list[dict]:
    return [
        {
            "urun": ad,
            "mevsimler": bilgi["mevsimler"],
            "azot_kg_donum": bilgi["gubre"]["azot_kg"],
            "fosfor_kg_donum": bilgi["gubre"]["fosfor_kg"],
            "gubre_kaynagi": GUBRE_KAYNAGI,
            "mazot_l_donum": MAZOT_TUKETIMI_LITRE_DONUM[ad],
            "mazot_kaynagi": bilgi.get("mazot_kaynagi", f"varsayim ({VARSAYILAN_MAZOT_KAYNAGI})"),
            "varsayimlar": varsayimlar_al(ad),
        }
        for ad, bilgi in URUNLER.items()
    ]
