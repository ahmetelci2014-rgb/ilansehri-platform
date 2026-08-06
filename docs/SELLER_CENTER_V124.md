# İlan Şehri v1.24 Satıcı Merkezi

## Amaç
İlan sahibinin yayın durumunu, performansı, alıcı ilgisini ve kalite eksiklerini dağınık hesap bölümleri yerine tek ekranda yönetmesi.

## Rotalar
- `/ilanlar/ilanlarim/`: sahip olunan ilanlar, filtreler ve performans özeti
- `/ilanlar/ilanlarim/toplu-islem/`: yalnız POST kabul eden sahiplik kontrollü toplu işlem

## İlan kartı sözleşmesi
- `data-v124-seller-center`: satıcı merkezi sayfası
- `data-v124-listing-card`: yönetilebilir ilan kartı
- `data-v124-listing-select`: toplu işlem seçimi
- `data-v124-bulk-form`: en fazla 50 ilanlık toplu işlem formu

## Güvenlik
- Liste ve işlemler `request.user` sahipliğiyle filtrelenir.
- Başka hesaba ait kimlikler gönderilse bile işleme alınmaz.
- İncelemede veya reddedilmiş ilan, normal kullanıcı tarafından doğrudan yayınlanamaz.
- Durum değiştiren bütün işlemler POST ve CSRF korumalıdır.
- `next` dönüş adresi yalnız aynı host için kabul edilir.

## Veri modeli
Yeni tablo veya alan eklenmez. Görüntülenme, favori, teklif, görüşme, durum ve süre bilgileri mevcut modellerden hesaplanır.

## Gizlilik ve indeksleme

- Satıcı Merkezi `noindex,nofollow` olarak sunulur.
- `/ilanlar/ilanlarim/` robots.txt içinde özel alan olarak işaretlenir.
- Service worker özel sayfa yanıtlarını çevrimdışı önbelleğe almaz.
- Randevu özelliği hesap ana akışında yalnız yaklaşan bir kayıt varsa görünür.
