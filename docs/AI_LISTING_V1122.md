# İlan Şehri v1.12.2.1 — Gemini ile Fotoğraftan İlan Hazırlama

## Amaç

Kullanıcı manuel ilan alanlarını doldurmadan önce 1–8 ürün fotoğrafı seçer. Google Gemini fotoğrafları analiz eder; yalnız doğrulanmış ve yeterli güvene sahip öneriler mevcut Django ilan formuna yerleştirilir. İlan hiçbir zaman otomatik yayınlanmaz.

## Kullanıcı akışı

1. `/ilanlar/yeni/` sayfası açılır.
2. Üstteki **AI ile Hızlı Başlangıç** alanına fotoğraflar eklenir.
3. **Yapay Zekâ ile İlan Hazırla** düğmesine basılır.
4. Görseller güvenli biçimde yeniden kodlanır ve metadata temizlenir.
5. Gemini görselleri ve aktif kategori kataloğunu birlikte analiz eder.
6. Yanıt JSON Schema sözleşmesine göre alınır ve sunucuda tekrar doğrulanır.
7. Yeterli güvene sahip başlık, açıklama, kategori, durum, marka, model, renk ve teknik bilgiler forma yazılır.
8. Emin olunmayan bilgiler kısa sorular halinde gösterilir.
9. Kullanıcı fiyatı, konumu ve eksik alanları tamamlar; bütün önerileri düzenleyebilir.
10. Normal ilan inceleme ve moderasyon akışı devam eder.

## Gemini kurulumu

Google AI Studio üzerinden bir Gemini API anahtarı oluşturulur. Sunucunun `.env` dosyasına şu değerler eklenir:

```env
GEMINI_API_KEY=BURAYA_GEMINI_ANAHTARI
GEMINI_API_BASE=https://generativelanguage.googleapis.com/v1beta
GEMINI_API_REVISION=2026-05-20
GEMINI_MODEL=gemini-3.6-flash
```

API anahtarı `.env.example`, kaynak kod, ekran görüntüsü veya GitHub commit'i içine yazılmaz.

Sonra Codespaces terminalinde:

```bash
python manage.py activate_gemini_ai --enable
```

Alternatif olarak Django teknik yönetiminde:

1. `/admin/ai_listing/aisettings/` açılır.
2. Sağlayıcı **Google Gemini görsel analizi** yapılır.
3. Model `gemini-3.6-flash` olarak ayarlanır.
4. **API bağlantısını test et** çalıştırılır.
5. Test başarılıysa **Özellik açık** seçilir.

## Gemini API yapısı

- Uç nokta: Gemini Interactions API.
- Görseller: güvenli JPEG olarak base64 satır içi veri.
- Çıktı: `application/json` ve katı JSON Schema.
- İstek saklama: `store=false`.
- Düşünme seviyesi: düşük; gereksiz gecikme ve çıktı maliyeti azaltılır.
- Toplam satır içi istek büyüklüğü 18 MB ile sınırlandırılır.

## Güvenlik ilkeleri

- Kaynak uzantısı ile gerçek görsel biçimi birlikte doğrulanır.
- Yalnız JPG, JPEG, PNG ve WEBP kabul edilir.
- En fazla 8 fotoğraf analiz edilir.
- Fotoğraflar EXIF yönü düzeltildikten sonra RGB JPEG olarak yeniden kodlanır.
- Analiz görselleri `AIAnalysis` kaydında saklanmaz; yalnız tek yönlü parmak izleri tutulur.
- Fiyat alanı AI şemasında bulunmaz; sağlayıcının ek fiyat alanı döndürmesi reddedilir.
- Kategori yalnız veritabanındaki aktif slug değerlerinden seçilebilir.
- Düşük güvenli alanlar otomatik uygulanmaz.
- Güvenlik sonucu `blocked` ise form alanları doldurulmaz.
- Yasaklı, tehlikeli, sahte veya mevzuata aykırı ürün şüphesinde ilan taslağı üretilmez.
- Görselde telefon, kimlik, plaka veya açık adres ihtimali varsa kullanıcı uyarılır.
- Kullanıcı onayı olmadan ilan yayınlanmaz.
- Aynı kullanıcı ve aynı fotoğraf grubunun aynı gün tekrar analizi yeniden istek oluşturmaz; mevcut sonuç döndürülür.

## Ücretsiz ve ücretli kullanım notu

Gemini Developer API belirli modeller için ücretsiz katman sunar. Ücretsiz katmanda gönderilen içerikler Google ürünlerini geliştirmek için kullanılabilir. Gerçek kullanıcı fotoğraflarının bulunduğu canlı sistemde ücretli katman ve güncel gizlilik şartları ayrıca değerlendirilmelidir.

## Operasyon ve gözlem

`AIAnalysis` kayıtları fotoğraf sayısı, sağlayıcı, model, işlem süresi, güven puanı, durum, hata kodu ve güvenlik uyarılarını tutar. `AIFieldChange` kayıtları AI önerisi ile kullanıcının yayınladığı son değer arasındaki farkı saklar.

## Bilinen sınırlar

- Görsel modeller marka, model, ürün durumu, sahte ürün ve kişisel bilgi tespitinde yüzde yüz doğruluk garantisi vermez.
- İnsan moderasyonu kaldırılmamıştır.
- Fiyat tahmini bu sürümde yoktur.
- Gerçek sağlayıcı testi için geçerli Gemini API anahtarı gerekir.
- Ücretsiz katman limitleri ve model erişimi Google tarafından değiştirilebilir.
