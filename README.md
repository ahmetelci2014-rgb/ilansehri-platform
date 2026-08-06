# İlan Şehri

> Güncel sürüm: **v1.12.2.4** — Gemini aktif olduğu hâlde ilan sayfasında pasif görünmesine neden olan şablon kalıtımı hatası düzeltildi.

İlan Şehri; ürün, araç, emlak, hizmet, ihtiyaç ve iş ilanlarını yerel kullanıcılarla buluşturan güven odaklı profesyonel marketplace platformudur.

## Çalışan ana modüller

- Konum ve kategori odaklı fotoğraflı marketplace akışı
- Fotoğrafla başlayan yapay zekâ ilan hazırlama, güvenli görsel analiz ve kullanıcı onayı
- Kategoriye özel gelişmiş arama, filtreleme, sıralama ve ilan karşılaştırma
- Favoriler, kayıtlı aramalar, son görüntülenenler ve fiyat düşüşü takibi
- Satıcı takip sistemi ve takip edilen satıcılardan yeni ilan akışı
- Teklif, karşı teklif, pazarlık geçmişi ve güvenli işlem kaydı
- Gelişmiş mesaj kutusu, alış/satış görüşmesi filtreleri ve görsel mesajlar
- Büyük fotoğraf galerisi, benzer ilanlar, satıcı vitrini ve kullanıcı değerlendirmeleri
- Üyelik, profil, telefon/e-posta doğrulama, güven puanı, engelleme ve şikâyet
- İlan moderasyonu, uyuşmazlık merkezi ve profesyonel yönetim paneli
- Yardım Merkezi, hesap içi destek talepleri, personel destek kuyruğu ve işlem günlüğü
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
- Yapay zekâ görsel analizi için OpenAI API anahtarı ve API hesabı
- Kullanıcı görselleri için kalıcı disk veya nesne depolama
- Gerçek şirket bilgileriyle hukukçu tarafından kontrol edilmiş yasal metinler

Ödeme aracılığı henüz aktif değildir. Güvenli işlem ekranı teklif, anlaşma ve teslim sürecini kayıt altına alır; para transferi tarafların sorumluluğundadır.


## v1.5 keşif deneyimi

- Canlı arama önerileri
- Kategori vitrinleri
- Kayıtlı arama yönetimi
- Filtrelenebilir bildirim merkezi
- İlan tamamlama göstergesi ve canlı önizleme


## v1.7 yayına hazırlık

Bu sürüm sitemap, robots, sosyal paylaşım meta verileri, ilan kalite puanı, fotoğraf optimizasyonu, anti-spam koruması ve yönetim büyüme raporlarını ekler. Canlı ortamda `PUBLIC_BASE_URL=https://alanadiniz.com` tanımlanması önerilir.


## v1.9 kullanıcı akışları ve hesap güvenliği

- Hesaba bağlı, cihazlar arasında erişilebilen ilan taslakları
- Yeni ilan ve ilan düzenleme taslağını kaydetme, sürdürme ve silme
- Eksiksiz şifremi unuttum ve şifre değiştirme ekranları
- Hesap ve Güvenlik merkezi
- Hesap verilerini JSON olarak indirme
- Şifre doğrulamalı hesap kapatma talebi ve talebi iptal etme
- Hesabım ekranında taslak sayısı ve hızlı taslak erişimi
- PWA özel sayfa önbellek güvenliği ve v1.9 önbellek sürümü

## v1.10 Destek ve Operasyon Merkezi

Yeni Yardım Merkezi ve hesap içi destek sistemi şu yollarla kullanılabilir:

- Yardım Merkezi: `/yardim/`
- Yeni destek talebi: `/yardim/talep/yeni/`
- Kullanıcının talepleri: `/yardim/taleplerim/`
- Personel destek kuyruğu: `/yardim/ekip/`

Destek talepleri kullanıcı hesabına bağlıdır. Kullanıcı yalnız kendi taleplerini görebilir. Personel yanıtları uygulama içi bildirim üretir; ekip içi notlar kullanıcıya gösterilmez. Destek işlemleri `StaffActionLog` kayıtlarında izlenir.


## v1.11 bildirim ve moderasyon operasyonu

- Kullanıcıya özel uygulama içi bildirim tercihleri
- Tür bazlı anlık e-posta bildirimleri
- Günlük veya haftalık bildirim özeti komutu
- Filtrelenebilir ve toplu işlem destekli moderasyon kuyruğu
- Zorunlu düzeltme notu ve personel işlem günlüğü

Bildirim özeti komutu:

```bash
python manage.py send_notification_digests
```

Ayrıntılar: `docs/NOTIFICATION_MODERATION.md`

## v1.12.2 Fotoğrafla Başlayan Yapay Zekâ İlan Akışı

- AI hızlı başlangıç alanı ilan formunun en üstüne taşındı.
- Kullanıcı önce 1–8 fotoğraf seçer; AI başlık, açıklama, kategori, durum, marka, model, renk, etiket ve teknik özellik önerir.
- Görsel yükleme alanı sürükle-bırak, mobil önizleme, tek tek silme ve kapak adayı göstergesiyle yeniden tasarlandı.
- OpenAI Responses API tabanlı gerçek görsel sağlayıcısı eklendi.
- Görseller analizden önce moderasyon, gerçek dosya türü, boyut, EXIF temizleme ve güvenli yeniden kodlama kontrollerinden geçer.
- Katı JSON şeması doğrulanmadan hiçbir AI alanı forma aktarılmaz.
- Düşük güvenli bilgiler soru olarak gösterilir; fiyat AI tarafından doldurulmaz.
- Mevcut manuel beş adımlı ilan verme akışı, taslaklar ve moderasyon korunur.

Kurulum ve güvenlik: `docs/AI_LISTING_V1122.md`

Dosya raporu: `docs/AI_LISTING_V1122_FILE_REPORT.md`
