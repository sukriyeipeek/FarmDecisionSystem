# Geliştirme yol haritası

## Bu değişiklik paketi

Ürün kataloğuyla eşleşen su profilleri ve açık kaynak/vekil ürün bilgileri;
su bütçeli optimizasyon; arayüzde yöntem, bütçe, plan karşılaştırması;
Open-Meteo hava bağlantısı ve kullanıcı girdili çevrimdışı sulama senaryosu;
Alembic başlangıç şeması ve güvenli geçiş dokümanı; atomik plan onayı;
JWT zorunlu claim denetimi; ortak frontend API adresi; CI ve Compose kurulumu.

## Sonraki doğrulama kapıları

1. İzmir ilçeleri için MGM/yerel ET0 ve etkili yağış verileriyle kalibrasyon;
   vekil ürünlerin gerçek ürün değerleriyle değiştirilmesi ve ziraat mühendisi onayı.
2. Mevcut MySQL veritabanının yedeği üzerinde legacy→güncel şema veri dönüşümü;
   gerçek veri kaybı testi; ardından uygulama ortamına geçiş.
3. Kalıcı sulama kayıtları, ekim tarihi, toprak ve parsel konumu; önerilen/uygulanan
   miktar farkını saklama. Bunlar olmadan ölçülmüş tasarruf veya CO2 iddiası yoktur.
4. Su riski: erişilebilir baraj/yeraltı suyu kaynağını doğrulama, sürümlü referans
   veri oluşturma ve AHP ağırlıklarını uzmanlarla tekrar değerlendirme.
5. Refresh token rotasyonu/iptali, parola sıfırlama ve giriş hız sınırı;
   bildirim sağlayıcısı ve kullanıcı onayı seçilince SMS/e-posta bağlantısı.
6. Kaynaklı bölgesel maliyetler, hasat sezonu fiyatı, çok mevsimli rotasyon ve
   model dosyalarının sürümlenmesi. Backtest sonuçlarıyla kalite eşiği belirleme.
7. 5–10 üreticilik pilot: su sayacı, uygulanan plan, gelir ve gider kaydı;
   sezon sonunda tahmin ve gerçekleşen etkiyi karşılaştırma.

Uydu/sensör ve kooperatif paneli, ölçülmüş pilot verilerinden sonra ele alınır.
Bu dokümandaki açık maddeler tamamlanmış özellik olarak sunulmaz.
