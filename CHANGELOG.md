# v1.12.2.4 — AI Şablon Etiketi Düzeltmesi

- `ai_listing_config` etiketi, Django şablon kalıtımında çalışması için `content` bloğunun içine taşındı.
- Gemini etkin olduğu hâlde HTML'de `data-ai-can-analyze="0"` üretilmesi düzeltildi.
- Sayfa seviyesinde aktif AI durumunu doğrulayan regresyon testi eklendi.
- API anahtarı, sağlayıcı veya veritabanı ayarlarında değişiklik yapılmadı.

# v1.12.2.3 — Kümülatif AI Kurulum Onarımı

- v1.12.2 ana paketi atlanarak Gemini fark paketinin yüklenmesi nedeniyle eksik kalan AI ve ilan dosyaları tek güncellemede birleştirildi.
- Eksik `SafetyBlockedError` sınıfı geri eklendi; Django başlangıcındaki ImportError giderildi.
- Fotoğrafla başlayan AI hızlı başlangıç şablonu, görsel yükleme JavaScript'i ve mobil CSS eksiksiz dahil edildi.
- İlan modelinin `color`, `search_tags` ve `technical_features` alanları yeniden dahil edildi.
- AI analiz, görsel hazırlama, form eşleme ve kullanıcı değişiklik kaydı dosyaları senkronlandı.
- Gemini sağlayıcısı, JSON şeması, güvenlik engeli ve yönetim ayarları tek sürüm altında birleştirildi.
- GitHub Actions'a AI servis import kontrolü eklendi; benzer eksiklikler migration aşamasından önce yakalanır.
- PWA ve statik dosya sürümü `v11223` olarak yenilendi.

# v1.12.2.2 — GitHub Actions statik dosya testi düzeltmesi

- Otomatik testler için ayrı `config.settings_test` ayarı eklendi.
- Testler artık manifest gerektirmeyen `StaticFilesStorage` kullanıyor.
- GitHub Actions test adımı açıkça `config.settings_test` ile çalışıyor.
- Testten önce `staticfiles` klasörü oluşturularak WhiteNoise uyarısı kaldırıldı.
- Canlı ortamın `CompressedManifestStaticFilesStorage` ayarı değiştirilmedi.

# İlan Şehri v1.12.2 — Fotoğrafla Başlayan Gerçek AI İlan Akışı

- AI hızlı başlangıcı ilan alanları doldurulmadan önce çalışacak şekilde formun en üstüne taşındı.
- Görsel yükleme alanı mobil öncelikli sürükle-bırak, fotoğraf sayacı, kapak adayı, tek tek silme ve tümünü temizleme özellikleriyle yeniden yazıldı.
- OpenAI Responses API üzerinden gerçek görsel analiz sağlayıcısı eklendi.
- OpenAI görsel moderasyonu ana analizden önce çalışır; riskli görsellerden ilan oluşturulmaz.
- Görseller EXIF temizlenerek, küçültülerek ve güvenli JPEG olarak yeniden kodlanarak servise gönderilir.
- Katı JSON şeması; başlık, açıklama, kategori, durum, marka, model, renk, etiket, teknik alan, kusur, soru ve güvenlik uyarılarını doğrular.
- Kategori yalnız aktif veritabanı kayıtlarına eşlenir; fiyat önerisi reddedilir.
- Düşük güvenli bilgiler otomatik uygulanmaz; kullanıcıya kısa soru gösterilir.
- `color`, `search_tags` ve `technical_features` ilan alanları eklendi.
- AI önerisi ile kullanıcının yayınladığı son değer arasındaki değişiklik kaydı korundu.
- Mevcut manuel ilan verme, taslak, üyelik, mesajlaşma, teklif ve moderasyon akışları kaldırılmadı.
- PWA önbelleği `ilansehri-v1122` olarak yenilendi.

# İlan Şehri v1.12.1.1 — AI Düğmesi Görünürlük Düzeltmesi

- AI kartı artık fotoğraf adımında sessizce kaybolmuyor.
- Özellik kapalıysa veya test sağlayıcısı normal kullanıcıya kapalıysa nedeni açıkça gösteriliyor.
- Yetkili kullanıcıda düğme fotoğraf seçilene kadar görünür fakat pasif kalıyor.
- Fotoğraf sayısı ve hazır olma durumu kart üzerinde anlık gösteriliyor.
- AI CSS ve JavaScript dosyalarına önbellek kırıcı sürüm eklendi.
- PWA önbelleği `ilansehri-v11211` olarak yenilendi.

# v1.11 — Bildirim ve Moderasyon Operasyonu

- Bildirim tercihleri modeli ve kullanıcı ayar ekranı eklendi.
- İsteğe bağlı uygulama içi bildirimler tür bazında kapatılabilir hale getirildi.
- İşlem, güvenlik, destek ve moderasyon bildirimleri kritik bildirim olarak korunur.
- Mesaj, teklif, işlem, ilan, fiyat, takip, değerlendirme ve sistem e-postaları ayrı ayrı seçilebilir.
- Günlük ve haftalık bildirim özeti komutu eklendi.
- Moderasyon kuyruğuna arama, tür, şehir, kalite ve sıralama filtreleri eklendi.
- En fazla 100 ilan için toplu onay ve toplu düzeltme isteği eklendi.
- Düzeltme notu zorunlu hale getirildi ve moderasyon işlemleri personel günlüğüne kaydedildi.
- Bildirim tercihleri hesap veri dışa aktarımına dahil edildi.
- PWA önbelleği v1.11 olarak yenilendi.

# Değişiklik Günlüğü

## v1.10 — Destek ve Operasyon Merkezi

- Herkese açık, aranabilir Yardım Merkezi ve güvenlik uyarıları eklendi.
- Üyeler için destek talebi oluşturma, talepleri listeleme, ayrıntı, yanıt ve kapatma akışı eklendi.
- Destek talebi ilan veya güvenli işlem kaydıyla ilişkilendirilebilir hale getirildi.
- Destek personeli için filtrelenebilir operasyon kuyruğu, atama, öncelik, durum, kullanıcı yanıtı ve ekip içi not sistemi eklendi.
- Ekip içi notlar kullanıcı ekranından kesin olarak ayrıldı.
- Destek yanıtlarında kullanıcıya uygulama içi bildirim gönderimi eklendi.
- Personel işlem günlüğü ve teknik admin kayıtları eklendi.
- Hesabım ve Profesyonel Yönetim Merkezi destek modülüyle birleştirildi.
- Destek talebi ve yanıtlarında temel hız sınırı eklendi.
- Destek akışları için otomatik yetki ve bildirim testleri eklendi.
- Mobil, tablet ve masaüstü için canlı mavi–turuncu destek tasarımı eklendi.
- PWA önbelleği v1.10 olarak yenilendi; özel destek sayfaları önbellek dışında bırakıldı.

## v1.9 — Kullanıcı Akışları ve Hesap Güvenliği

- Hesaba bağlı ilan taslakları, şifre yenileme, veri indirme ve hesap kapatma talebi eklendi.
