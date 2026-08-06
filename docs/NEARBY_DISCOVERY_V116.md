# İlan Şehri v1.16.0 — Yakındaki İlanlar ve Konum Tabanlı Keşif

## Kullanıcı akışı

- Ana sayfa ve ilan sonuçlarında **Yakınımda** düğmesi bulunur.
- Tarayıcı konum izni verirse koordinatlar yalnız arama URL'sinde kullanılır.
- İlanlar seçilen 25 km yarıçapta kesin Haversine mesafesiyle filtrelenir ve yakından uzağa sıralanır.
- İlan kartında yaklaşık mesafe kilometre olarak gösterilir.
- Konum izni reddedilirse profil veya seçili şehir–ilçe filtresine güvenli biçimde geri dönülür.
- Kullanıcının anlık koordinatları profil alanlarına veya ayrı bir konum geçmişine yazılmaz.

## Teknik yaklaşım

PostGIS zorunluluğu getirilmedi. Önce veritabanında güvenli bir koordinat sınır kutusu uygulanır; kalan adaylarda kesin küresel mesafe Python tarafında hesaplanır. Bu yaklaşım SQLite geliştirme ortamı ile PostgreSQL canlı ortamında aynı sonucu verir.

- Gizlilik için konum koordinatları yaklaşık 100 metre hassasiyete yuvarlanır; açık adres kaydedilmez.
