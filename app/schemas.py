import math

from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from typing import Annotated, Literal, Optional
from datetime import datetime

# Ciftcinin beyan ettigi gecmis verim (ton/donum); 30 ustu girdi hatasi kabul edilir.
GecmisVerim = Annotated[float, Field(gt=0, le=30)]
Strateji = Literal["dengeli", "temkinli"]
SulamaYontemi = Literal["damla", "yagmurlama", "salma"]
OptimizasyonModu = Literal["dengeli", "su_tasarruflu"]
Sezon = Literal["İlkbahar", "Yaz", "Sonbahar", "Kış"]

# Kullanıcı şemalrı ( kayıt ve giriş yapmak için)

class KullaniciBase(BaseModel):

    ad_soyad:str
    email:EmailStr
    yas:int | None = None
    cinsiyet:str | None = None
    telefon:str | None = None


class KullaniciCreate(KullaniciBase):
    sifre:str


class KullaniciLogin(BaseModel):

    email:EmailStr
    sifre:str


class KullaniciUpdate(BaseModel):

    ad_soyad:str
    yas:int | None=None
    cinsiyet:str | None=None
    telefon:str | None=None


class KullaniciResponse(KullaniciBase):

    kullanici_id:int
    kayit_tarihi:datetime
    model_config = ConfigDict(from_attributes=True)


class TarlaUrunCreate(BaseModel):
    urun_id: int
    donum: float


class TarlaCreate(BaseModel):
    tarla_adi: str
    ilce_id: int

    urunler: list[TarlaUrunCreate] #kullanıcı aynı tarlaya birden fazla ürün ekebilir o yüzden bunları liste olarak tutmak laızm

class RiskTahminRequest(BaseModel):
    ilce: str
    urun: str
    donum: float = Field(..., gt=0)
    sezon: str

class RiskLogResponse(BaseModel):
    log_id: int
    ilce_adi : str
    urun_adi:str
    sezon: str
    girilen_donum: float
    kota_doluluk: float | None
    cv_fiyat: float | None
    mazot_tahmini: float | None
    mazot_riski: float | None
    enflasyon_tahmini: float | None
    enflasyon_riski: float | None
    gubre_guncel: float | None
    gubre_riski: float | None
    genel_risk: float | None
    risk_seviyesi: str | None
    sorgu_tarihi: datetime

    model_config = ConfigDict(from_attributes=True)

class KarHesabiRequest(BaseModel):
    ilce: str
    urun: str
    donum: float = Field(..., gt=0)
    sezon: str
    sulama_maliyeti: float | None = None
    iscilik_maliyeti: float | None = None
    tohum_maliyeti: float | None = None
    gecmis_verimler: list[GecmisVerim] | None = Field(default=None, max_length=10)

class FiyatTahminRequest(BaseModel):
    sezon: str
    urun : str

class OptimizationTarlaRequest(BaseModel):
    sezon: Sezon
    tarla_id:int
    bos_donum: float = Field(..., gt=0)
    secilen_urunler: Optional[list[str]] = None
    strateji: Strateji = "dengeli"
    gecmis_verimler: dict[str, list[GecmisVerim]] | None = None
    # iscilik, tohum, sulama, kira gibi gubre ve mazot disindaki giderler (TL/donum)
    ek_maliyet_donum: float = Field(default=0, ge=0)
    su_butcesi_m3: float | None = Field(default=None, ge=0)
    sulama_yontemi: SulamaYontemi = "damla"
    optimizasyon_modu: OptimizasyonModu = "dengeli"

    @field_validator("bos_donum", "ek_maliyet_donum")
    @classmethod
    def tarla_sayilari_sonlu_olmali(cls, value):
        if not math.isfinite(value):
            raise ValueError("Alan ve maliyet değerleri sonlu olmalıdır")
        return value

    @field_validator("su_butcesi_m3")
    @classmethod
    def su_butcesi_sonlu_olmali(cls, value):
        if value is not None and not math.isfinite(value):
            raise ValueError("su_butcesi_m3 sonlu bir sayı olmalıdır")
        return value

class OptimizationManuelRequest(BaseModel):
    ilce_adi: str
    donum:float = Field(..., gt=0)
    sezon : Sezon
    secilen_urunler:Optional[list[str]] = None
    strateji: Strateji = "dengeli"
    gecmis_verimler: dict[str, list[GecmisVerim]] | None = None
    # iscilik, tohum, sulama, kira gibi gubre ve mazot disindaki giderler (TL/donum)
    ek_maliyet_donum: float = Field(default=0, ge=0)
    su_butcesi_m3: float | None = Field(default=None, ge=0)
    sulama_yontemi: SulamaYontemi = "damla"
    optimizasyon_modu: OptimizasyonModu = "dengeli"

    @field_validator("donum", "ek_maliyet_donum")
    @classmethod
    def manuel_sayilari_sonlu_olmali(cls, value):
        if not math.isfinite(value):
            raise ValueError("Alan ve maliyet değerleri sonlu olmalıdır")
        return value

    @field_validator("su_butcesi_m3")
    @classmethod
    def su_butcesi_sonlu_olmali(cls, value):
        if value is not None and not math.isfinite(value):
            raise ValueError("su_butcesi_m3 sonlu bir sayı olmalıdır")
        return value

class OneriOnaylaUrun(BaseModel):
    urun_adi:str
    donum:float = Field(..., gt=0)

    @field_validator("donum")
    @classmethod
    def donum_sonlu_olmali(cls, value):
        if not math.isfinite(value):
            raise ValueError("donum sonlu bir sayı olmalıdır")
        if abs(value * 100 - round(value * 100)) > 1e-8:
            raise ValueError("donum en fazla iki ondalık basamak içermelidir")
        return value

class OnerıOnaylaRequest(BaseModel):
    tarla_id:int
    hesaplanan_toplam_kar:float
    urunler: list[OneriOnaylaUrun]

    @field_validator("hesaplanan_toplam_kar")
    @classmethod
    def kar_sonlu_olmali(cls, value):
        if not math.isfinite(value):
            raise ValueError("hesaplanan_toplam_kar sonlu bir sayı olmalıdır")
        return value

class AdminKullaniciResponse(BaseModel):
    kullanici_id: int
    ad_soyad: str
    email: str
    telefon: str | None = None
    yas: int | None = None
    cinsiyet: str | None = None
    is_admin: bool


class AdminUrunResponse(BaseModel):
    urun_id: int
    urun_adi: str
    aktif: bool
