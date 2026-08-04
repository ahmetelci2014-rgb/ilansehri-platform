# V1.12.1 — Yapay Zekâ ile İlan Hazırla Çekirdeği

Bu sürüm mevcut ilan oluşturma sistemini değiştirmeden yapay zekâ özelliğinin güvenli çekirdeğini ekler.

## Eklenen güvenlik katmanları

- Özellik varsayılan olarak kapalıdır.
- API anahtarı ve servis adresi yalnız `.env` üzerinden okunur.
- JPG, JPEG, PNG ve WEBP doğrulaması gerçek dosya içeriği üzerinden yapılır.
- En fazla 8 görsel kabul edilir.
- Görseller analiz öncesi küçültülür, JPEG'e çevrilir ve EXIF bilgileri atılır.
- Görseller veritabanında veya analiz kayıtlarında saklanmaz; yalnız tek yönlü parmak izleri tutulur.
- Kullanıcı ve site geneli günlük limit vardır.
- Aynı fotoğrafların ve aynı istek anahtarının tekrar gönderilmesi engellenir.
- Sağlayıcı çıktısı katı JSON sözleşmesiyle doğrulanır.
- Fiyat alanı ilk sürüm sözleşmesinde yasaktır.
- Engelli içerik sonucu forma aktarılmaz.

## Sağlayıcılar

- `mock`: Geliştirme ve otomatik test için. Gerçek görsel tanıma yapmaz.
- `http_json`: Değiştirilebilir harici servis adaptörü. `AI_LISTING_API_URL` ve `AI_LISTING_API_KEY` ister.

## Sonraki aşama

V1.12.2'de seçilecek gerçek görsel sağlayıcısına özel adaptör ve kontrollü prompt uygulanacaktır. V1.12.3'te sonuçlar ilan formuna mobil uyumlu biçimde aktarılacaktır.

## Form entegrasyon kabuğu

Yönetici özelliği açtığında fotoğraf adımında mavi-turuncu AI kartı görünür. Test sağlayıcısı yalnız personel hesabında görünür. Düşük güvenli alanlar otomatik doldurulmaz; sorular ve uyarılar kullanıcıya gösterilir. Analiz kimliği ilanla ilişkilendirilir ve kullanıcı tarafından değiştirilen alanlar denetim kaydına yazılır.
