# İlan Şehri v1.17.0 — Kayıtlı Aramalar ve Akıllı İlan Bildirimleri

## Özellikler

- Kullanıcı mevcut ilan filtrelerini güvenli bir beyaz liste üzerinden kaydeder.
- Her arama için **Anlık**, **Günlük özet** veya **Kapalı** seçilir.
- Anlık modda yeni ilan yayına alındığı anda uygun kayıtlı aramalar kontrol edilir.
- Günlük modda `marketplace_maintenance` komutu son kontrolden beri yayınlanan ilanları tek özet bildirimde toplar.
- `SavedSearchMatch` tekil kaydı aynı arama–ilan çifti için tekrar bildirim üretilmesini engeller.
- Kayıtlı arama adı ve bildirim sıklığı hesap ekranından düzenlenir.
- Aynı filtreler tekrar kaydedilirse ikinci kayıt açılmaz; mevcut arama güncellenir.
- Kullanıcı başına 30 kayıtlı arama ve saatlik kayıt oluşturma sınırı uygulanır.

## Düzeltilen mevcut sorunlar

- Liste ekranı ile bakım komutunun farklı filtre kümeleri kullanması giderildi; ikisi aynı filtre motoruna bağlandı.
- Kategori, teslimat, durum, yakıt, vites, hizmet/iş alanları, metrekare, kilometre, fiyat düşüşü ve takip filtresi artık bildirimlerde de doğru uygulanır.
- Taslakta uzun süre bekleyip sonradan yayınlanan ilanlar `created_at` yerine `published_at` üzerinden yakalanır.
- Kayıtlı aramaya desteklenmeyen POST alanlarının yazılması ve sınırsız URL verisi saklanması engellendi.
- Aynı aramanın tekrar tekrar çoğalması engellendi.
- Kayıtlı aramalar, favoriler ve teklif merkezi PWA özel sayfa listesine; kayıtlı aramalar ve favoriler robots engeline eklendi.

## Veritabanı

Bu sürüm migration gerektirir. Kurulum akışı `makemigrations` ve `migrate` komutlarını otomatik çalıştırır.

- Gizlilik için konum koordinatları yaklaşık 100 metre hassasiyete yuvarlanır; açık adres kaydedilmez.

## Zamanlama

Anlık uyarılar ilan yayınlanırken oluşur. Günlük özetler için canlı hosting zamanlayıcısı günde bir kez `bash scripts/run_daily_maintenance.sh` çalıştırmalıdır.
