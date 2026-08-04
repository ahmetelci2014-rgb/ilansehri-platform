# İlan Şehri Değişiklik Günlüğü

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

## v1.12.1 — Yapay Zekâ ile İlan Hazırla çekirdeği

- Yapay zekâ özelliği ayrı `apps.ai_listing` uygulamasına alındı.
- Tekil yönetim ayarları, kullanıcı/site günlük limitleri ve API bağlantı testi eklendi.
- Analiz, hata, güvenlik ve kullanıcı değişiklik kayıt modelleri eklendi.
- JPG/JPEG/PNG/WEBP gerçek dosya doğrulaması, EXIF temizleme ve güvenli küçültme eklendi.
- Aynı istek ve aynı görsel grubunun tekrar analiz edilmesini engelleyen koruma eklendi.
- Fiyatı kesinlikle kabul etmeyen kontrollü JSON doğrulama katmanı eklendi.
- Değiştirilebilir `mock` ve `http_json` sağlayıcı katmanı eklendi.
- Özellik varsayılan olarak kapalıdır; mevcut ilan verme akışı etkilenmez.
