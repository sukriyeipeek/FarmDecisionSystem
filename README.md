# Tarımsal Karar Destek Sistemi

## SuAkıl geliştirme paketi

Öneri ekranı artık su bütçesi (m³), sulama yöntemi ve su tasarruflu planlama
seçeneklerini destekler. Aynı girdilerle iki planı karşılaştırabilir, toplam su
tahmini ve su başına kârı görebilirsiniz. Su miktarları kaynaklı yaklaşık
planlama değerleridir; yerel ölçüm ve gerçekleşmiş tasarruf değildir.

- [Su hesabı ve kaynaklar](docs/water-model.md)
- [Hava tabanlı sulama API'si ve çevrimdışı senaryo](docs/irrigation.md)
- [Veritabanı migration ve mevcut kurulum geçişi](docs/database.md)
- [Docker Compose ile kurulum](docs/deployment.md)
- [Geliştirme yol haritası](docs/roadmap.md)

Tüm frontend API çağrıları `VITE_API_URL` kullanır (yerelde varsayılan
`http://localhost:8000`, Compose içinde `/api`). Ortam değişkeni build sırasında
uygulanır. API şemaları ve yeni su uç noktaları `/docs` adresindedir.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
![CatBoost](https://img.shields.io/badge/CatBoost-FFCC00)
![PuLP](https://img.shields.io/badge/PuLP-optimizasyon-2E7D32)

Tarımsal Karar Destek Sistemi; geçmiş tarımsal veriler, makine öğrenmesi ve matematiksel optimizasyon yöntemlerini kullanarak üreticilere **veriye dayalı ekim planı ve risk analizi** sunan bir web uygulamasıdır.

Sistem, İzmir'in altı ilçesinde (Bayındır, Bergama, Menderes, Tire, Torbalı, Ödemiş) 15 sebze ürünü için çalışır. Kullanıcı tarlasını ve arazi büyüklüğünü girer; sistem gelecek sezon için fiyat tahmini, risk skoru ve tahmini kâr hesaplar, ardından araziyi ürünler arasında en dengeli şekilde paylaştıran bir ekim planı önerir.

Projenin amacı yalnızca en yüksek gelir potansiyeline sahip ürünü önermek değil; **kârlılık, üretim kapasitesi, arz riski ve ekim sınırlarını birlikte değerlendirerek daha dengeli bir üretim planı oluşturmaktır.**

## Özellikler

| Modül | Açıklama |
| --- | --- |
| Fiyat tahmini | Ürün ve sezon bazında gelecek dönem hal fiyatı (TL/kg) |
| Risk analizi | Arz fazlası, fiyat oynaklığı ve girdi maliyeti risklerini birleştiren 0–100 arası skor |
| Kârlılık analizi | Tahmini verim, üretim, gelir, gübre ve mazot giderleri ile net kâr; çiftçinin kendi geçmiş verimi isteğe bağlı |
| Belirsizlik | Ölçülmüş hata payına dayanan fiyat ve kâr aralığı, başabaş fiyatı ve zarar olasılığı |
| Ekim optimizasyonu | Kâr ve güvenliği birlikte gözeten, kota ve çeşitlendirme kısıtlı ekim planı; "dengeli" ve "temkinli" yaklaşım |
| Tarla yönetimi | Tarla ekleme, ekili ürünler ve onaylanan planın tarlaya işlenmesi |
| Hal fiyatları | Günlük İzmir hal fiyatları; kaynak erişilemezse ulusal ortalama veya son kayıtlı fiyatlar |
| Yönetim paneli | Kullanıcı yetkilendirme ve ürünlerin aktif/pasif yapılması |

## Sistem Mimarisi

```text
┌───────────────────┐   HTTP / JSON   ┌──────────────────────────┐
│  React (Vite)     │ ──────────────► │  FastAPI                 │
│  Kullanıcı arayüzü│                 │  ├─ Fiyat tahmini        │
└───────────────────┘                 │  ├─ Risk analizi         │
                                      │  ├─ Kâr hesabı           │
                                      │  └─ Ekim optimizasyonu   │
                                      └─────┬──────────────┬─────┘
                                            │              │
                                 SQLAlchemy │              │ Eğitilmiş modeller
                                            ▼              ▼ ve veri setleri
                                     ┌────────────┐  ┌─────────────────┐
                                     │   MySQL    │  │ models/, data/  │
                                     └────────────┘  └─────────────────┘
```

Karar akışı:

```text
Kullanıcı bilgileri ─► Bölgeye uygun ürünler ─► Fiyat tahmini ─► Kârlılık analizi
                                                                       │
              Optimal ekim planı ◄─ PuLP optimizasyonu ◄─ Risk ve kota analizi
```

## Teknolojiler

| Katman | Teknoloji |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic, passlib (bcrypt) |
| Veritabanı | MySQL |
| Veri işleme | Pandas, NumPy |
| Makine öğrenmesi | CatBoost (fiyat), XGBoost (ekim alanı ve üretim), Ridge regresyon (mazot ve enflasyon), Scikit-learn |
| Optimizasyon | PuLP (CBC çözücü) |
| Frontend | React 19, Vite, React Router, Recharts |

## Veri Kaynakları

| Veri | Kaynak |
| --- | --- |
| Sebze hal fiyatları (2014–2026) | İzmir Büyükşehir Belediyesi açık veri |
| İlçe bazında ekim alanı ve üretim | TÜİK |
| Enflasyon (TÜFE) | TCMB EVDS |
| Mazot fiyatları | Mevsimlik fiyat verileri |
| Güncel üre fiyatı | tradingeconomics.com |
| Günlük hal fiyatları | İzmir Büyükşehir Belediyesi; yedek olarak T.C. Ticaret Bakanlığı Hal Kayıt Sistemi |

Ham veriler temizlenir, aylık değerler mevsimlik ortalamalara çevrilir ve model girdileri için birleştirilir. Bu adımlar `data/processed/code` klasöründedir.

## Yöntem

### Fiyat tahmini

Tahmin, hedef sezonla aynı mevsimdeki en son fiyattan başlar ve beklenen enflasyonla büyütülür. CatBoost modeli bu tabanı ürün ve mevsime özgü sapmalara göre düzeltir:

```text
fiyat = taban fiyat × exp( yıl farkı × ln(1 + enflasyon) + model düzeltmesi )
```

Fiyatlar 2014–2026 arasında yaklaşık 35 kat arttığından, model doğrudan fiyat seviyesini değil enflasyonun açıklayamadığı değişimi öğrenir. Bu sayede ağaç tabanlı modellerin eğitimde görmediği fiyat seviyelerine ulaşamama sorunu ortadan kalkar. Mazot tahmini Ridge regresyonundan gelir.

Enflasyon tahmini, Ridge modelinin tahmini ile son gözlenen enflasyonun ortalamasıdır. Zaman serisi testinde model tek başına "enflasyon olduğu yerde kalır" varsayımından daha kötü çıkmış, ikisinin ortalaması en düşük hatayı vermiştir (bkz. Model Değerlendirmesi).

### Belirsizlik

Tek bir fiyat tahmini, %30 civarındaki hata payını gizler. Bu nedenle her tahminle birlikte bir aralık verilir. Aralık, modelin zaman serisi testindeki gerçek hatalarından hesaplanır:

```text
hata          = ln(gerçek fiyat / tahmin)              her ürün ve tahmin ufku (1–4 sezon) için
aralık        = tahmin × exp(hataların %2,5 ve %97,5 yüzdelikleri)
ürüne özel    = w × ürünün yüzdelikleri + (1 − w) × ufkun yüzdelikleri,   w = n / (n + 15)
```

Fiyatı daha oynak ürünlerin (örneğin lahana) aralığı daha geniş, istikrarlı ürünlerinki (örneğin brokoli) daha dardır. Aralığın gerçekte ne kadar tuttuğu, her seferinde bir tahmin başlangıcı dışarıda bırakılarak ölçülür. Nominal %95'lik aralık, görülmemiş yıllarda gerçek fiyatı **%76** oranında kapsamıştır; uygulama bu ölçülmüş oranı gösterir. Fiyat rejimi yıldan yıla değiştiği için geçmiş hatalar geleceği olduğundan dar gösterir; daha dar bir %80'lik aralık yalnızca %62 kapsadığı için kullanılmamıştır.

Aralıktan türetilen göstergeler:

| Gösterge | Tanım |
| --- | --- |
| Kâr aralığı | Aralığın alt ve üst fiyatıyla hesaplanan net kâr |
| Başabaş fiyatı | Giderleri tam karşılayan satış fiyatı (TL/kg) |
| Zarar olasılığı | Geçmiş hatalar bugünkü tahmine uygulandığında fiyatın başabaşın altında kalma oranı; yalnızca fiyat belirsizliğini kapsar |

Aralıkları yeniden üretmek için: `python -m app.scripts.price_intervals` (sonuç `models/price_intervals.json`).

### Risk analizi

Beş risk bileşeni 0–100 arasında hesaplanır ve AHP (Analitik Hiyerarşi Süreci) ile belirlenen ağırlıklarla birleştirilir:

| Bileşen | Ağırlık | Ölçüt |
| --- | --- | --- |
| Kota doluluğu | 0.38 | İlçede beklenen ekim alanının dolma oranı |
| Fiyat oynaklığı | 0.29 | Enflasyondan arındırılmış fiyatların değişim katsayısı |
| Gübre | 0.16 | Güncel fiyatın tarihsel ortalamadan sapması |
| Mazot | 0.09 | Tahmini fiyatın tarihsel ortalamadan sapması |
| Enflasyon | 0.08 | Tahmini enflasyonun tarihsel ortalamadan sapması |

Toplam skor dört seviyeye ayrılır: Güvenli (0–25), Orta Risk (25–50), Riskli (50–75), Çok Riskli (75–100).

### Kârlılık analizi

```text
verim (ton/dönüm) = ilçenin tahmini üretimi / tahmini ekim alanı
gelir             = dönüm × verim × tahmini fiyat
gider             = gübre + mazot (+ isteğe bağlı sulama, işçilik ve tohum)
net kâr           = gelir − gider
```

Gübre ihtiyacı, Tarım ve Orman Bakanlığı'nın ürün bazındaki azot ve fosfor değerlerinden hesaplanır. Ürün sabitleri `app/services/product_catalog.py` dosyasında tek yerde tutulur. Ölçülmüş değer yerine yaklaşık değer kullanılan kalemler (şu an domates dışındaki ürünlerin mazot tüketimi) yanıtta `varsayimlar` olarak listelenir; tamamı `GET /urun/varsayimlar` adresindedir.

Çiftçi kendi geçmiş verimlerini girerse ilçe ortalamasıyla birleştirilir (kredibilite ağırlıklandırması):

```text
verim = w × kendi ortalaması + (1 − w) × ilçe verimi,     w = n / (n + 2),  n = girilen yıl sayısı
```

Tek yıllık beyan ilçe değerini 1/3, beş yıllık kayıt 5/7 oranında etkiler; tek bir iyi ya da kötü yıl planı tek başına belirlemez.

### Ekim optimizasyonu

Ekim planı bir doğrusal programlama problemi olarak çözülür:

```text
maksimize et   Σ xᵢ · skorᵢ             xᵢ: ürün i'ye ayrılan alan (dönüm)

kısıtlar       Σ xᵢ ≤ boş alan
               xᵢ ≤ 0.4 × boş alan       tek ürüne en fazla %40
               xᵢ ≤ kotaᵢ                ilçedeki beklenen ekim alanı
               xᵢ ≥ 0

skorᵢ = 0.7 × kâr skoruᵢ + 0.3 × (100 − riskᵢ)
```

Yalnızca hedef mevsimde ekilebilen ve beklenen kârı pozitif olan ürünler aday olarak değerlendirilir. Kârlı ürün kalmayan alan, zarar eden bir ürünle doldurulmak yerine "boş bırakılması önerilen alan" olarak raporlanır.

Kâr skoru iki şekilde hesaplanabilir:

| Yaklaşım | Kâr skoru neye göre | Ne zaman |
| --- | --- | --- |
| Dengeli (varsayılan) | Beklenen kâr | Ortalama getiriyi en yükseğe çıkarmak |
| Temkinli | Fiyat aralığının alt ucundaki kâr | Kötü bir sezonda zararı sınırlamak |

Örnek (Bayındır, yaz, 100 dönüm): temkinli plan fiyatı çok oynak kırmızı lahana yerine pırasa seçer; beklenen kâr %0,7 düşer, kötü senaryodaki kâr %2,5 artar. Tüm ilçe ve sezonlarda iki yaklaşım yaklaşık her on senaryodan birinde farklı plan önerir. Öneri ekranındaki "diğer giderler (TL/dönüm)" alanı girilmezse kâr yüksek, zarar olasılığı düşük görünür.

## Model Değerlendirmesi

Fiyat modeli, gerçek kullanımı taklit eden **kayan başlangıçlı zaman serisi testi** ile değerlendirilmiştir: 2021–2025 arasındaki her başlangıç noktasında model yalnızca o tarihe kadarki veriyle eğitilmiş ve sonraki dört mevsimi tahmin etmiştir (261 tahmin).

| Yöntem | MAPE | Sapma |
| --- | --- | --- |
| Geçen yılın aynı mevsim fiyatı | %38.6 | −%40.2 |
| Geçen yıl × enflasyon | %26.5 | −%7.1 |
| İlk model (doğrudan fiyat tahmini) | %31.2 | −%29.8 |
| **Mevcut model** | **%28.4** | **−%1.4** |

İlk model rastgele veri bölmesiyle ölçüldüğünde R² 0.95 gösteriyordu; ancak zaman serisinde bu yöntem gelecekteki verinin eğitime sızmasına yol açar. Zamana göre yapılan test, ilk modelin fiyatları sistematik olarak yaklaşık %30 düşük tahmin ettiğini ortaya koymuş ve mevcut yapıya geçişi belirlemiştir.

Bu tablo hedef sezonun gerçekleşen enflasyonunu kullanır, yani yalnızca fiyat modelini ölçer. Uygulamada enflasyon da tahmin edildiği için, aynı test tahmini enflasyonla da yapılmıştır (uçtan uca):

| Yöntem | MAPE | Sapma |
| --- | --- | --- |
| Geçen yılın aynı mevsim fiyatı | %38.6 | −%40.2 |
| Geçen yıl × tahmini enflasyon | %30.6 | −%11.9 |
| **Mevcut model** | **%33.2** | **−%6.5** |

Mevcut model sistematik sapmada daha iyi, ortalama mutlak hatada ise "geçen yıl × enflasyon" yönteminden biraz geride; bu fark modelin ileride sadeleştirilip sadeleştirilmeyeceği değerlendirilirken dikkate alınmalıdır.

Enflasyon tahmini de aynı yöntemle (2019'dan itibaren 28 başlangıç, 1–4 sezon ileri) test edilmiştir. Hata yıllık enflasyon puanıdır:

| Yöntem | Ortalama mutlak hata |
| --- | --- |
| Ridge modeli | 16.5 puan |
| Enflasyon olduğu yerde kalır | 14.3 puan |
| **İkisinin ortalaması (uygulamada kullanılan)** | **14.3 puan** |

Testleri yeniden çalıştırmak için:

```bash
python -m app.scripts.price_backtest
python -m app.scripts.inflation_backtest
python -m app.scripts.price_intervals
```

## Kurulum

### Gereksinimler

- Python 3.10 veya üstü (3.11 ile test edilmiştir)
- MySQL 8
- Node.js 20 veya üstü

### Backend

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Proje kök dizininde `.env.example` dosyasını `.env` olarak kopyalayıp doldurun:

```text
DATABASE_URL=mysql+pymysql://<kullanıcı>:<şifre>@localhost:3306/tarim_karar_analiz
JWT_SECRET=<en az 32 karakterlik rastgele anahtar>
```

Anahtar üretmek için: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
`JWT_SECRET` en az 32 karakter olmalıdır. `DATABASE_URL` zorunludur; eski `sifre=` değişkeni artık okunmaz. Oturum süresi 1–1440 dakika aralığında olmalıdır.

### Veritabanı

```sql
CREATE DATABASE tarim_karar_analiz CHARACTER SET utf8mb4;
```

Yeni ve boş veritabanında tabloları önce migration ile oluşturun. Mevcut kurulum
için [geçiş talimatını](docs/database.md) izleyin; eski şemaya doğrudan stamp uygulamayın.

```bash
python -m alembic upgrade head
```

Ardından başlangıç verilerini bir kez yükleyin:

```bash
mysql -u root -p tarim_karar_analiz < database_seed.sql
python -m app.scripts.insert_kota
```

### Frontend

```bash
cd frontend
npm install
```

## Çalıştırma

```bash
uvicorn app.main:app_tarim --reload
```

```bash
cd frontend
npm run dev
```

| Adres | İçerik |
| --- | --- |
| `http://localhost:5173` | Web uygulaması |
| `http://localhost:8000/docs` | Etkileşimli API dokümantasyonu |

## Proje Yapısı

```text
app/
├── main.py           FastAPI uygulaması
├── routes.py         API uç noktaları
├── models.py         Veritabanı modelleri
├── schemas.py        İstek ve yanıt şemaları
├── auth.py           JWT üretimi ve yetki bağımlılıkları
├── services/         Fiyat, risk, kâr, optimizasyon ve veri servisleri
│   └── product_catalog.py  Ürün adı, mevsim, gübre ve mazot sabitleri (tek kaynak)
└── scripts/          Model eğitimi, veri yükleme ve backtest betikleri
data/
├── raw_data/         Ham veriler
└── processed/        Temizleme betikleri ve işlenmiş veri setleri
models/               Eğitilmiş modeller
frontend/             React uygulaması
tests/                Otomatik testler
database_seed.sql     İlçe ve ürün başlangıç verileri
```

## API

Başlıca uç noktalar aşağıdadır; tam liste `/docs` adresindedir. `/kullanici/giris` bir `access_token` döndürür; kimlik doğrulaması gerektiren uç noktalar `Authorization: Bearer <token>` başlığı bekler ve kullanıcıyı token'dan belirler (istekte `kullanici_id` gönderilmez). `/admin/*` uç noktaları yalnızca yönetici hesaplara açıktır.

| Metot | Uç nokta | Açıklama |
| --- | --- | --- |
| POST | `/tahmin/fiyat` | Ürün ve sezon için fiyat tahmini |
| POST | `/tahmin/risk` | Risk analizi |
| POST | `/kar/hesapla` | Kârlılık analizi |
| POST | `/oneri/tarla_getir` | Kayıtlı tarla için ekim planı |
| POST | `/oneri/manual` | İlçe ve alan girilerek ekim planı |
| POST | `/oneri/onayla` | Önerilen planın tarlaya işlenmesi |
| GET | `/istatistikler/hal-fiyatlari` | Günlük hal fiyatları |

## Testler

```bash
python -m pytest
```

Testler veritabanı veya internet bağlantısı gerektirmez.

## Bilinen Kısıtlar ve Yol Haritası

- **Kimlik doğrulama:** JWT ile oturum yönetimi vardır; ancak refresh token, parola sıfırlama ve giriş denemesi sınırı henüz yoktur. Token tarayıcıda `localStorage`'da tutulur; yayına alırken HttpOnly çerez değerlendirilmelidir.
- **Maliyet kalemleri:** Varsayılan kâr hesabı yalnızca gübre ve mazot giderlerini içerir; işçilik, tohum, sulama ve kira kullanıcı tarafından girilir. Bu kalemler girilmezse zarar olasılığı olduğundan düşük görünür. Kaynaklı bölgesel varsayılanlar (örneğin TEPGE ürün maliyet çalışmaları) eklenmelidir.
- **Ekim ve hasat mevsimi:** Fiyat, ürünün ekildiği mevsim için tahmin edilir. Ekimden aylar sonra hasat edilen ürünlerde (örneğin yazın ekilip sonbaharda hasat edilen brokoli), satış fiyatı hasat mevsiminden alınmalıdır. Ürün kataloğuna hasat mevsimi eklenmesi planlanmaktadır.
- **Belirsizlik aralığı:** Yalnızca beş tahmin başlangıcından türetildiği için yaklaşıktır ve görülmemiş yıllarda %76 kapsamıştır. Verim ve maliyet belirsizliği henüz aralığa dahil değildir.
- **Mazot tüketimi:** Yalnızca domates için ölçülmüş değer vardır; diğer ürünlerde bu değer kullanılır ve kullanıcıya varsayım olarak gösterilir.
- **Dış veri kaynakları:** Güncel hal ve gübre fiyatları web kaynaklarından alınır. Hal fiyatları için yedek kaynaklar mevcuttur.

## Ekip

- Şükriye İpek
- Çağlar Özkan
