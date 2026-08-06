# v1.16.0 Yakındaki İlanlar ve Konum Tabanlı Keşif

## Amaç
Kullanıcının izin verdiği konumu kullanarak koordinatı bulunan ilanları yaklaşık mesafeye göre göstermek; koordinatı bulunmayan ilanları ise kullanıcının şehir/ilçe bilgisine göre ikincil sonuç olarak sunmak.

## Çalışma biçimi
- Tarayıcı konumu yalnız kullanıcı `Konumumu kullan` düğmesine bastığında ister.
- Arama yarıçapı 5, 10, 25, 50, 100 veya 200 km olabilir.
- Önce veritabanında yaklaşık bir koordinat kutusu uygulanır, ardından Haversine hesabıyla gerçek dairesel mesafe kontrol edilir.
- Koordinatı olmayan ilanlar, kullanıcının profilindeki veya filtresindeki şehir/ilçeyle eşleşiyorsa sonuçların sonunda `Aynı bölgede` etiketiyle gösterilir.
- Geçici arama koordinatları URL yerine Django oturumunda tutulur ve kayıtlı aramalara yazılmaz.
- İlan sahibi isterse ilan formunda konumunu işaretler. Koordinatlar yaklaşık 10 metre hassasiyete yuvarlanır ve ilan detayında gösterilmez.

## Ölçekleme notu
Bu sürüm SQLite ve standart PostgreSQL ile çalışan sınırlı aday kutusu + Haversine yaklaşımını kullanır. İlan sayısı çok büyüdüğünde PostGIS ve coğrafi indeks geçişi önerilir.

## Gizlilik
- Konum izni zorunlu değildir.
- Kullanıcının arama konumu yalnız oturum verisinde geçici tutulur; hesap profiline kaydedilmez.
- İlan koordinatı yalnız ilan sahibi açıkça `Konumumu işaretle` dediğinde ilan kaydına yazılır.
- Tam adres, enlem veya boylam halka açık şablonlarda gösterilmez.
