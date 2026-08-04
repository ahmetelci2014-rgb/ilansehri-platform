# İlan Şehri v1.0 — Tamamlanmış MVP

İlan Şehri; ürün, araç, emlak, hizmet, ihtiyaç ve iş ilanlarını tek platformda buluşturan; kullanıcının ilanını kendisinin yönetebildiği veya **İlan Şehri Tam Yönetim** hizmetine bırakabildiği güven odaklı yerel pazar yeridir.

## V1.0'da çalışan ana modüller

- Üyelik, profil, telefon/e-posta doğrulama ve güven puanı
- Ürün, araç, emlak, hizmet, ihtiyaç ve iş ilanları
- Kategoriye özel alanlar ve Türkiye şehir/ilçe/mahalle seçimi
- En fazla 10 fotoğraf, kapak seçimi, silme ve sürükleyerek sıralama
- Gelişmiş arama, filtreleme, favoriler ve kayıtlı aramalar
- Özel mesajlaşma, görsel eki, engelleme ve bildirim merkezi
- Teklif gönderme, kabul, ret, geri çekme ve tekrar teklif koruması
- Alıcı–satıcı güvenli işlem kaydı, çift taraflı teslim onayı ve uyuşmazlık
- Tamamlanan işlem sonrası puan ve yorum
- İlan moderasyonu, şikâyet ve uyuşmazlık yönetimi
- Tam Yönetim müşteri ve operasyon panelleri
- Görev ortağı başvurusu, ekip onayı, görev pazarı, teslim ve kazanç kaydı
- PWA/çevrimdışı sayfa, Docker, PostgreSQL, WhiteNoise ve Gunicorn hazırlığı
- GitHub Actions üzerinde migration, güvenlik, statik dosya ve otomatik test kontrolleri

## Codespaces ile çalıştırma

```bash
git pull origin main
pkill -f "python manage.py runserver" || true
bash scripts/start_codespace.sh
```

Komut migrationları üretir, veritabanını günceller, kategorileri ve statik dosyaları hazırlar, sistemi port `8000` üzerinde başlatır.

### Demo verileri

Yalnız geliştirme ortamında:

```bash
python manage.py seed_demo --with-admin
```

Demo hesaplar:

- `demo_satici` / `Demo1234!`
- `demo_alici` / `Demo1234!`
- `demo_partner` / `Demo1234!`
- `demo_admin` / `DemoAdmin1234!`

Bu bilinen şifrelerle oluşturulan hesaplar canlı ortamda kullanılmamalıdır.

## Yerel kurulum

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations accounts listings managed_services partners
python manage.py migrate
python manage.py seed_categories
python manage.py createsuperuser
python manage.py runserver
```

## Docker

```bash
docker compose up --build
```

## Düzenli bakım

Aşağıdaki komut süresi dolan ilanları kapatır, eski doğrulama kodlarını temizler ve kayıtlı arama bildirimlerini üretir:

```bash
python manage.py marketplace_maintenance
```

Canlı sunucuda bu komutun saatlik veya günlük zamanlayıcıya bağlanması gerekir.

## Canlıya geçişte zorunlu dış ayarlar

- Güçlü `DJANGO_SECRET_KEY`
- PostgreSQL `DATABASE_URL`
- Alan adı ve `CSRF_TRUSTED_ORIGINS`
- SMTP e-posta hesabı
- Telefon doğrulaması için `SMS_WEBHOOK_URL` ve isteğe bağlı `SMS_WEBHOOK_TOKEN`
- Kullanıcı görselleri için kalıcı disk veya nesne depolama
- Gerçek şirket/veri sorumlusu bilgileriyle yasal metinlerin hukukçu kontrolü

Ödeme aracılığı v1.0'da aktif değildir. Güvenli işlem ekranı, teklif ve teslim sürecini kayıt altına alır; para transferi tarafların sorumluluğundadır.
