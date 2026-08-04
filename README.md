# İlan Şehri — Django Başlangıç Sürümü

İlan Şehri; ürün, araç, emlak, hizmet, ihtiyaç ve iş ilanlarını tek yerel platformda birleştiren, kullanıcının ilanını kendisinin yönetebildiği veya İlan Şehri Tam Yönetim hizmetine bırakabildiği yeni nesil pazar yeri projesidir.

## Sürüm 0.4 — Profesyonel arayüz ve pazar yeri deneyimi

- Ücretsiz kullanıcı kaydı ve otomatik giriş
- Kullanıcı hesabım paneli
- Çoklu ilan fotoğrafı yükleme
- İlan oluşturma ve ilan sahibi tarafından düzenleme
- Gelişmiş ilan filtreleri
- İlan detayından teklif gönderme
- “İlan Şehri yönetsin” seçiminde otomatik Tam Yönetim kaydı
- Geliştirme ortamında otomatik yayın seçeneği

- GitHub Codespaces ile hosting almadan tarayıcıda önizleme
- Port 8000 otomatik açılış ve önizleme
- Üyelik, ilan, tam yönetim, teklif ve yetki testleri
- GitHub Actions üzerinde migration ve tam test çalıştırma

- Profesyonel ana sayfa, marka başlığı ve mobil alt menü
- Premium ilan kartları ve gelişmiş kategori deneyimi
- Adım adım ilan oluşturma ve fotoğraf önizleme
- Gelişmiş ilan detay, teklif ve güvenli işlem ekranı
- Yenilenmiş kullanıcı paneli, giriş ve üyelik ekranları

## Bu ilk sürümde bulunan çekirdek

- Özel kullanıcı modeli: bireysel, kurumsal, hizmet veren ve görev ortağı
- Ürün, araç, emlak, hizmet, ihtiyaç ve iş ilan türleri
- Satılık, kiralık, takas, arıyorum ve hizmet seçenekleri
- `Kendim yöneteceğim / İlan Şehri yönetsin` seçimi
- Kategori, şehir, ilçe ve mahalle alanları
- Teklif veri modeli
- Tam yönetim başvuru modeli
- Görev ortağı seviyeleri ve ücretli görev modeli
- Yönetim paneli
- Mobil uyumlu başlangıç arayüzü
- PostgreSQL ve Docker hazırlığı
- GitHub Actions kontrolü


## GitHub Codespaces ile önizleme

1. GitHub deposunda **Code** butonuna basın.
2. **Codespaces** sekmesini açın.
3. **Create codespace on main** seçeneğine basın.
4. Kurulum tamamlanınca port 8000 otomatik açılır ve İlan Şehri önizlemesi görünür.
5. Önizleme açılmazsa terminalde `bash scripts/start_codespace.sh` çalıştırın.

İlk kurulum; bağımlılıkları kurar, migrationları oluşturur, veritabanını hazırlar ve başlangıç kategorilerini ekler.

## Yerel kurulum

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations accounts listings managed_services partners
python manage.py migrate
python manage.py seed_categories
python manage.py createsuperuser
python manage.py runserver
```

Ardından `http://127.0.0.1:8000` ve yönetim için `http://127.0.0.1:8000/admin` adresini açın.

## Docker ile

```bash
docker compose up --build
```

## Önemli

Bu depo ilk çalışan mimari iskelettir. Sonraki sürümlerde sırayla kayıt ekranları, çoklu fotoğraf yönetimi, konum/mesafe arama, mesajlaşma, teklif ekranları, tam yönetim operasyon paneli, görev pazarı, doğrulama, ödeme ve yapay zekâlı ilan oluşturma eklenecektir.
