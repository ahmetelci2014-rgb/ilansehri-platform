# AI Düğmesi Görünürlük Düzeltmesi

## Sorunun nedeni

V1.12.1 arayüzü AI kartını yalnız bütün sunucu koşulları sağlandığında ve JavaScript fotoğraf seçimini algıladığında gösteriyordu. Özellik kapalı, test sağlayıcısı normal kullanıcıya kapalı veya tarayıcı eski JavaScript dosyasını kullanıyorsa kart tamamen görünmüyordu.

## Düzeltme

- Kart yeni ilan formunun fotoğraf adımında görünür tutulur.
- Kullanım kapalıysa nedenini gösterir.
- Yetkili kullanıcıda fotoğraf seçilene kadar düğme pasiftir.
- Fotoğraf seçimi sonrası hazır mesajı görünür.
- Statik dosyalara sürüm sorgusu ve PWA önbellek yenilemesi eklenmiştir.
