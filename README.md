# İlan Şehri v1.2 — Profesyonel Marketplace

İlan Şehri; ürün, araç, emlak, hizmet, ihtiyaç ve iş ilanlarını tek platformda buluşturan güven odaklı yerel pazar yeridir.

## Çalışan ana modüller

- Konum ve kategori odaklı marketplace ana sayfası
- Yoğun fotoğraflı ilan kartları ve mobil iki sütunlu akış
- Kategoriye özel gelişmiş filtreler ve sıralama
- Favoriler, kayıtlı aramalar, son görüntülenenler ve ilan karşılaştırma
- Büyük fotoğraf galerisi, benzer ilanlar ve satıcı vitrini
- Üyelik, profil, doğrulama ve güven puanı
- Mesajlaşma, teklif, güvenli işlem kaydı, uyuşmazlık ve yorum
- İlan moderasyonu, şikâyet merkezi ve profesyonel yönetim paneli
- Tam Yönetim operasyonları ve Kazanç Ağı görev sistemi
- PWA, çevrimdışı sayfa, Docker, PostgreSQL, WhiteNoise ve Gunicorn hazırlığı
- GitHub Actions üzerinde migration, güvenlik, statik dosya ve otomatik test kontrolleri

## Codespaces ile çalıştırma

```bash
git pull origin main
pkill -f "python manage.py runserver" || true
bash scripts/start_codespace.sh
```

Sistem port `8000` üzerinde açılır.

## Demo verileri

```bash
python manage.py seed_demo --with-admin
```

Demo hesaplar:

- `demo_satici` / `Demo1234!`
- `demo_alici` / `Demo1234!`
- `demo_partner` / `Demo1234!`
- `demo_admin` / `DemoAdmin1234!`

Profesyonel yönetim merkezi: `/yonetim/`

Teknik Django yönetimi: `/admin/`

Bu bilinen şifrelerle oluşturulan hesaplar canlı ortamda kullanılmamalıdır.

## Düzenli bakım

```bash
python manage.py marketplace_maintenance
```

Bu komut süresi dolan ilanları kapatır, eski doğrulama kodlarını temizler ve kayıtlı arama bildirimlerini üretir.

## Canlıya geçişte gerekli dış ayarlar

- Güçlü `DJANGO_SECRET_KEY`
- PostgreSQL `DATABASE_URL`
- Alan adı ve `CSRF_TRUSTED_ORIGINS`
- SMTP e-posta hesabı
- Telefon doğrulaması için SMS servisi
- Kullanıcı görselleri için kalıcı disk veya nesne depolama
- Gerçek şirket bilgileriyle hukukçu tarafından kontrol edilmiş yasal metinler

Ödeme aracılığı henüz aktif değildir. Güvenli işlem ekranı, teklif ve teslim sürecini kayıt altına alır; para transferi tarafların sorumluluğundadır.
