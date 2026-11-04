# Su planlama arayüzü

## Ekim önerisi (`/oneriler`)

`POST /oneri/manual` ve `POST /oneri/tarla_getir` mevcut alanlarını ve
`strateji` (`dengeli` / `temkinli`) anlamını korur. İki isteğe de şu alanlar eklenir:

- `su_butcesi_m3`: boş giriş için `null`; aksi halde sonlu, sıfır veya pozitif sayı.
  Ondalık virgül desteklenir. `0` sınırsız bütçe anlamına gelmez.
- `sulama_yontemi`: `damla` (varsayılan), `yagmurlama`, `salma`.
- `optimizasyon_modu`: `dengeli` (varsayılan), `su_tasarruflu`.

Örneğin manuel istek:

```json
{
  "ilce_adi": "Tire",
  "donum": 10,
  "sezon": "Yaz",
  "secilen_urunler": null,
  "strateji": "temkinli",
  "ek_maliyet_donum": 0,
  "su_butcesi_m3": 5000,
  "sulama_yontemi": "damla",
  "optimizasyon_modu": "dengeli"
}
```

Yanıt, `success` ve `plan` içeren tek tarla özetinden oluşan listedir. Ürün
kartlarında `water_per_decare_m3`, `estimated_water_m3`,
`water_efficiency_tl_m3` ve açılır `water_assumptions` gösterilir. Toplam su için
tarla özetinin `estimated_water_m3` değeri kullanılır; yoksa ancak tüm ürünlerin
su verileri tam olduğunda toplam alınır. Bütçe `water_budget_m3` yanıtından
gösterilir. Toplam TL/m³ = toplam tahmini net kâr / toplam tahmini su;
oranların ortalaması alınmaz. Eksik veri veya sıfır suya bölme `Veri yok` gösterir.

“Öneri Al” tek istek gönderir. İsteğe bağlı “Modları Karşılaştır” düğmesi aynı
girdilerin bir kopyasıyla iki isteği başlatır; yalnızca `optimizasyon_modu`
değişir. Aynı bütçe ve `strateji` iki istekte de korunur. İki yanıt da HTTP ve
tarla düzeyinde başarılı olmalıdır; su ve kâr değerleri tam olmadan farklar
gösterilmez. Fark yönü **Su tasarruflu − Dengeli** olarak etiketlenir. Seçili
modun planı gösterilir ve yalnızca mevcut onay düğmesiyle kaydedilebilir.
Girdi değişiklikleri sonuçları temizler ve bekleyen eski yanıtları geçersiz
kılar. Otomatik mod karşılaştırması, yeniden deneme veya periyodik istek yoktur.

Su değerleri ve karşılaştırma farkları geçici model tahminleridir; ölçülmüş
tüketim, gerçekleşmiş tasarruf veya her durumda tasarruf garantisi sunulmaz.

## Günlük sulama (`/sulama`)

Sayfa oturum gerektirir; token yoksa `/login` sayfasına yönlendirir. Navbar
bağlantısı giriş yapmış kullanıcıya gösterilir. `App.jsx`, gerçek dosya adına
uygun küçük harfli `components/navbar` yolunu kullanır.

“Sulama Tahmini Al” ile `POST /sulama/oneri` çağrılır. Sayısal sınırlar backend
`IrrigationRequest` şemasını izler:

- `latitude`: −90…90; `longitude`: −180…180.
- `area_decare`: 0'dan büyük, en fazla 1.000.000.
- `kc`: 0'dan büyük, en fazla 3.
- `current_deficit_mm`: 0…1000; `allowed_deficit_mm`: 0'dan büyük, en fazla 1000.
- `irrigation_method`: `damla` (varsayılan), `yagmurlama`, `salma`.
- `effective_rain_fraction`: 0…1; varsayılan 1.

Çevrimiçi mod varsayılandır ve `forecast` alanı **gönderilmez**. Sunucu
Open-Meteo tahminini alır. Hata durumunda otomatik demo verisi veya yeniden
deneme kullanılmaz. Kullanıcı açıkça demo modunu seçerse kendi JSON hava
verisini girmelidir; gizli örnek veri gönderilmez. `forecast` 1–7 ardışık,
benzersiz ve sıralı `YYYY-MM-DD` günü, her gün için sonlu sayısal `et0_mm`
(0…100) ve `rain_mm` (0…1000) içerir. Fazladan alanlar kabul edilmez.

```json
[{"date":"2026-06-01","et0_mm":4,"rain_mm":0}]
```

Yanıtta veri kaynağı (`open-meteo` / `user`) açıkça gösterilir. Özet
`total_irrigation_volume_m3` ve `final_deficit_mm`, günlük kartlar `days`,
varsayımlar `warnings` alanlarından alınır. Demo sonuçları kullanıcı senaryosu
olarak etiketlenir. Girdi değişiklikleri bekleyen yanıtları ve mevcut sonucu
geçersiz kılar. Otomatik sulama işlemi yapılmaz.

## API ve doğrulama

Bu sayfaların tüm çağrıları ortak `API_URL` kullanır:
`import.meta.env.VITE_API_URL`, verilmezse `http://localhost:8000`.
Sondaki `/` kaldırılır. Mevcut `authFetch` token başlığı ve 401 durumundaki
oturum kapatma davranışı korunur.

Doğrulanan kontroller:

- `cd frontend` ardından `npm run build`: başarılı. Vite, mevcut büyük JS
  paketi için 500 kB uyarısı verir; derleme hatası değildir.
- Değişen altı JS/JSX dosyası için ESLint: başarılı.
- Node assert kontrolleri: boş/0/negatif/sonlu olmayan su bütçesi; eksik veya
  sıfır su verisi; toplam TL/m³; sulama şeması sınırları; çevrimiçi istekte
  `forecast` alanının olmaması; demo günlerinin tarih ve sıralama doğrulaması:
  başarılı.

Canlı backend ve tarayıcı üzerinden tam entegrasyon testi bu değişikliğin
doğrulamasına dahil değildir.

Elle kontrol senaryoları: boş/0/negatif/sonsuz su bütçesi; her iki kaynak ve
optimizasyon modu; başarılı/başarısız karşılaştırma; istek sırasında girdi
değiştirme; çevrimiçi hava hatasının demo üretmemesi; demo modundan çevrimiçi
moda geçince `forecast` alanının gönderilmemesi.
