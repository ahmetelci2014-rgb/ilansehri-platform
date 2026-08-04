# İlan Şehri v1.0 Teknik Mimarisi

- Python 3.13 ve Django 5.2
- Geliştirmede SQLite, canlı ortamda PostgreSQL
- Sunucu taraflı Django Templates ve responsive PWA
- WhiteNoise statik dosya sunumu
- Gunicorn uygulama sunucusu
- Docker ve Docker Compose
- Ortam değişkenleriyle güvenlik ve servis yapılandırması
- GitHub Actions ile migration, sistem, dağıtım, statik dosya ve test kontrolü

## Uygulamalar

- `accounts`: hesap, profil, doğrulama, güven ve engelleme
- `listings`: ilan, görsel, favori, teklif, işlem, yorum, mesaj, bildirim ve moderasyon
- `managed_services`: Tam Yönetim müşteri ve operasyon akışı
- `partners`: görev ortağı, görev pazarı ve kazanç kayıtları
- `core`: ana sayfa, yasal sayfalar, PWA, sağlık kontrolü ve yönetim komutları

## Ölçekleme yolu

İlk canlı sürümden sonra medya depolama/CDN, Redis, Celery, PostGIS, WebSocket ve harici yapay zekâ servisleri ayrı katmanlar olarak eklenebilir.
