# Hava tabanlı sulama senaryosu

Arayüzde giriş yapıp **Sulama** ekranını açın. Enlem/boylam, dönüm, bitki katsayısı
(Kc), başlangıç kök bölgesi su açığı ve izin verilen açık eşiği girilir.
Kc ve eşik için yerel ziraat mühendisi/toprak ölçümü kullanılmalıdır.

Kimlik doğrulamalı API: `POST /sulama/oneri`. İstek alanları `latitude`,
`longitude`, `area_decare`, `kc`, `current_deficit_mm`, `allowed_deficit_mm`,
`irrigation_method` (damla/yagmurlama/salma), isteğe bağlı `effective_rain_fraction`.
`GET /su/katalog` ürün planlama profillerini ve varsayımlarını döndürür.

Çevrimiçi mod [Open-Meteo](https://open-meteo.com/en/docs) üzerinden İstanbul
saat diliminde yedi günlük ET0 ve yağmur verisi alır. Sabit HTTPS adresi,
bağlantı/okuma zaman aşımı ve 15 dakikalık, 256 girdilik önbellek vardır.
Eksik/hatalı veri veya kesinti 503 döndürür. Eski veri otomatik kullanılmaz.
Kullanımdan önce sağlayıcının ticari kullanım ve kota koşullarını kontrol edin.

Çevrimdışı demo için kullanıcı açıkça `forecast` listesi gönderir:

```json
[{"date":"2026-11-05","et0_mm":5,"rain_mm":0}]
```

Bir ile yedi ardışık gün kabul edilir. Sonuç `source=user` ve demo olarak
işaretlenir. Çevrimiçi hata otomatik demo verisiyle kapatılmaz.

Günlük bilanço: açık = max(0, önceki açık + ET0×Kc − etkili yağış).
Açık eşiğe ulaşınca kalan açığın tamamını karşılayan tahmini sulama hesaplanır.
Brüt mm = net mm / uygulama verimi; m³ = brüt mm × dönüm.
Fazla yağış drenajdır. Gün içi yağış zamanlaması, toprak kapasitesi, su stresi
ve sensör geri bildirimi modellenmez. Sonuç öneri senaryosudur; otomatik
sulama, bildirim gönderimi ve gerçekleşmiş tasarruf kaydı oluşturmaz.
