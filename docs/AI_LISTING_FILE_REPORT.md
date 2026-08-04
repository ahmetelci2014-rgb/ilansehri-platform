# V1.12.1 Dosya Dosya Değişiklik Raporu

## Yeni uygulama: `apps/ai_listing`

- `models.py`: Tekil AI ayarları, analiz kayıtları ve kullanıcı değişiklik kayıtları.
- `services/image_processor.py`: JPG/JPEG/PNG/WEBP içerik doğrulaması, EXIF temizleme, güvenli küçültme ve JPEG yeniden kodlama.
- `services/schemas.py`: Fiyat alanını reddeden katı JSON sözleşmesi ve alan uzunluğu/listesi doğrulamaları.
- `services/providers.py`: Değiştirilebilir test ve harici JSON servis sağlayıcıları.
- `services/analysis.py`: Limit, eşzamanlı istek kilidi, tekrar analizi önleme, kategori eşleme, güvenlik sonucu ve denetim kaydı orkestrasyonu.
- `views.py` / `urls.py`: Oturum gerektiren analiz, durum ve kullanıcıya ait analiz sonucu uçları.
- `admin.py`: Yapay Zekâ Ayarları, bağlantı testi, analiz/hata/güvenlik kayıtları ve istatistikler.
- `signals.py`: Migration sonrasında kapalı varsayılan ayar kaydını otomatik oluşturur.
- `templatetags/ai_listing_tags.py`: Özellik kapalıyken ilan formunu değiştirmeyen güvenli görünürlük kontrolü.
- `tests.py`: Özellik kapalı, test sağlayıcısı yetkisi, görsel dönüştürme, JSON doğrulama, limit, idempotency ve kullanıcı izolasyonu testleri.

## Mevcut dosyalardaki sınırlı değişiklikler

- `templates/listings/form.html`: Fotoğraf adımına yalnız özellik açıldığında görünen AI kartı ve analiz kimliği alanı.
- `static/js/v112-ai.js`: Yükleniyor durumu, güven puanına göre form doldurma, AI etiketi, soru/uyarı gösterimi ve normal forma geri dönüş.
- `static/css/v112-ai.css`: Mevcut mavi–turuncu temayla uyumlu mobil öncelikli görünüm.
- `apps/listings/views.py`: İlan kaydından sonra AI önerisi ile son kullanıcı değerlerini karşılaştıran, hata halinde ilan yayınını durdurmayan denetim çağrısı.
- `apps/core/views.py`: PWA özel sayfa koruması, AI operasyon istatistikleri, robots ve sürüm bilgisi.
- `templates/core/staff_dashboard.html`: AI durum, kullanım, başarısızlık ve güvenlik engeli kartı.
- `templates/base.html`: Yeni CSS/JS dosyaları ve v1.12.1 sürüm etiketi.
- `config/settings.py` / `config/urls.py`: Ayrı uygulama kaydı ve özel AI URL alanı.
- `.env.example`: Kaynak koda anahtar yazmadan servis yapılandırması.
- `.github/workflows/tests.yml`, `scripts/start_codespace.sh`, `scripts/bootstrap_production.sh`: Yeni uygulama migration ve sistem kontrolüne dahil edildi.

## Bilerek bu aşamada yapılmayanlar

- Gerçek sağlayıcıya özel görsel prompt ve API adaptörü henüz bağlanmadı.
- Fiyat tahmini eklenmedi.
- Renk, etiket ve serbest teknik özellikler henüz `Listing` alanlarına yazılmıyor; doğrulanmış analiz kaydında tutuluyor ve kullanıcıya öneri olarak gösteriliyor.
- Özellik varsayılan olarak kapalıdır. Test sağlayıcısı normal kullanıcılara gösterilmez.

Bu sınırlar mevcut ilan, üyelik, mesaj, teklif, destek ve moderasyon akışlarını riske atmamak için kasıtlıdır.
