# İlan Şehri v1.3 — Pazarlık, Fiyat Takibi ve Satıcı Ağı

İlan Şehri; ürün, araç, emlak, hizmet, ihtiyaç ve iş ilanlarını yerel kullanıcılarla buluşturan güven odaklı profesyonel marketplace platformudur.

## Çalışan ana modüller

- Konum ve kategori odaklı fotoğraflı marketplace akışı
- Kategoriye özel gelişmiş arama, filtreleme, sıralama ve ilan karşılaştırma
- Favoriler, kayıtlı aramalar, son görüntülenenler ve fiyat düşüşü takibi
- Satıcı takip sistemi ve takip edilen satıcılardan yeni ilan akışı
- Teklif, karşı teklif, pazarlık geçmişi ve güvenli işlem kaydı
- Gelişmiş mesaj kutusu, alış/satış görüşmesi filtreleri ve görsel mesajlar
- Büyük fotoğraf galerisi, benzer ilanlar, satıcı vitrini ve kullanıcı değerlendirmeleri
- Üyelik, profil, telefon/e-posta doğrulama, güven puanı, engelleme ve şikâyet
- İlan moderasyonu, uyuşmazlık merkezi ve profesyonel yönetim paneli
- Tam Yönetim operasyonları ve İlan Şehri Kazanç Ağı görev sistemi
- PWA, Docker, PostgreSQL, WhiteNoise ve Gunicorn canlı sunucu hazırlığı
- GitHub Actions migration, güvenlik, statik dosya ve otomatik test kontrolleri

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

Teklif ve pazarlık merkezi: `/ilanlar/tekliflerim/`

Takip edilen satıcılar: `/hesap/takip-ettiklerim/`

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

Ödeme aracılığı henüz aktif değildir. Güvenli işlem ekranı teklif, anlaşma ve teslim sürecini kayıt altına alır; para transferi tarafların sorumluluğundadır.


## v1.5 keşif deneyimi

- Canlı arama önerileri
- Kategori vitrinleri
- Kayıtlı arama yönetimi
- Filtrelenebilir bildirim merkezi
- İlan tamamlama göstergesi ve canlı önizleme
