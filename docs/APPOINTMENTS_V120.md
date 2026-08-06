# İlan Şehri v1.20.0 — Güvenli Randevu ve Teslim Planlama

## Amaç

Mesajlaşan gerçek alıcı ve satıcının ürün inceleme, teslim veya hizmet görüşmesini platform içinde tarih ve saatle planlamasını sağlamak. Randevu sistemi ödeme aracılığı yapmaz ve herkese açık konum paylaşmaz.

## Kullanıcı akışı

1. Kullanıcı mevcut ilan görüşmesini açar.
2. Görüşme türünü, tarih-saatini, tahmini süreyi ve gerekli buluşma bilgisini yazar.
3. Diğer taraf uygulama içi bildirim alır.
4. Davet edilen kullanıcı öneriyi onaylar veya reddeder.
5. Aktif randevu taraflardan biri tarafından iptal edilebilir.
6. Onaylanan randevu yaklaşan 24 saate girdiğinde iki tarafa bir kez hatırlatma gönderilir.

## Güvenlik ve gizlilik

- Randevu yalnız ilgili konuşmanın alıcı ve satıcısı tarafından oluşturulabilir ve görüntülenebilir.
- Buluşma bilgileri ilan veya kullanıcı profilinde herkese açık hale gelmez.
- Bildirim metninde kesin buluşma noktası gösterilmez.
- Yüz yüze ve teslim randevularında şehir, ilçe ve anlaşılır buluşma noktası zorunludur.
- Not alanında bağlantı, telefon numarası ve e-posta paylaşımı engellenir.
- Randevu en az 30 dakika, en fazla 90 gün sonrası için oluşturulabilir.
- Taraflardan birinin aynı saat aralığındaki bekleyen veya onaylı randevusu yeni çakışan öneriyi engeller.
- Engellenmiş kullanıcılar arasında yeni randevu oluşturulamaz.
- Hız sınırı, bir kullanıcının saatte en fazla sekiz öneri oluşturmasına izin verir.

## Bakım

`python manage.py marketplace_maintenance` komutu:

- tarihi geçmiş ve hâlâ yanıt bekleyen randevuları kapatır,
- yaklaşan 24 saat içindeki onaylı randevular için tek seferlik hatırlatma oluşturur.

Canlı ortamda `bash scripts/run_daily_maintenance.sh` günlük çalıştırılmalıdır.

## Şema

Yeni `Appointment` modeli `ensure_v120_schema` komutuyla eski kurulumlarda geriye uyumlu biçimde doğrulanır. Codespaces, üretim başlangıcı ve GitHub Actions akışları bu komutu otomatik çalıştırır.
