# Değişiklik Günlüğü

## v1.19.0.2 — Mobil denetim giriş ve kapsam düzeltmesi

- Mobil denetimde giriş formu dışındaki gizli arama düğmesinin seçilmesine yol açan geniş submit seçicisi kaldırıldı.
- Giriş formuna kararlı `data-mobile-audit-login` kancası eklendi; alıcı, satıcı, partner ve yönetici oturumları bu forma bağlandı.
- Denetim artık beklenen 126 ekranın tamamlanıp tamamlanmadığını ayrıca doğrular ve eksik kapsamı açıkça raporlar.
- Mobil rapor sürümü `VERSION` dosyasından okunur; sonraki sürümlerde sabit sürüm uyuşmazlığı oluşmaz.
- Mobil sözleşme kontrolü, geniş submit seçicisinin yeniden eklenmesini ve giriş kancasının kaybolmasını engeller.
- v1.19.0.1 dinamik service worker testi kümülatif olarak korunur.

## v1.19.0 — İşlem tamamlama, güvenli teslim ve karşılıklı değerlendirme

- İşlem tamamlama, teslim aşaması başlamadan kullanılamayacak şekilde sıkılaştırıldı; teslim aşamasını yalnız satıcı başlatabilir.
- Elden ve yerinde teslimler için alıcının oluşturduğu 15 dakika geçerli, beş deneme sınırına sahip tek kullanımlık teslim kodu eklendi.
- Teslim kodu açık metin olarak saklanmaz; güvenli parola hash'i olarak tutulur ve doğrulanınca temizlenir.
- İşlem oluşturma, teslim başlangıcı, kod üretimi/doğrulaması, taraf onayları, uyuşmazlık ve moderasyon kararları `TransactionEvent` geçmişine kaydedilir.
- Değerlendirmeler kör yayın akışına geçirildi: iki taraf da yazarsa aynı anda, tek taraf yazarsa 7 gün sonra yayınlanır.
- Değerlendirme süresi tamamlanmış işlemden sonra 30 günle sınırlandı; düşük puanlarda açıklama ve herkese açık iletişim bilgisi kontrolleri eklendi.
- Teklif Merkezi'ne aktif ve geçmiş güvenli işlemler eklendi; kullanıcı veri ihracı yeni teslim/değerlendirme alanlarıyla genişletildi.
- Güven puanı, sonradan çözülenler dahil uyuşmazlık geçmişini işlem olaylarından hesaba katar.
- Eski veritabanları için `ensure_v119_schema` komutu; Codespaces, üretim ve CI başlangıçlarına eklendi.
- Mobil Görsel Denetim'den `continue-on-error` kaldırıldı ve `--strict` etkinleştirildi.

## v1.18.0 — Güvenilir satıcı profili ve dolandırıcılık koruması

- Satıcı profillerine açıklanabilir 0–100 güven puanı, doğrulama rozetleri, hesap yaşı, ortalama yanıt süresi ve işlem güvenilirliği eklendi.
- Kullanıcı şikâyeti akışı; kendi hesabını şikâyet engeli, hız sınırı, açık kayıt tekrar engeli ve ilişkili ilan seçimiyle güçlendirildi.
- Şüpheli ilan içeriği, olağan dışı düşük fiyat, riskli mesaj ve başka hesaplarda kullanılan fotoğraf için `AccountRiskEvent` inceleme kayıtları eklendi.
- İlan görsellerine yerel SHA-256 parmak izi eklendi; görseller üçüncü taraf servise gönderilmeden hesaplar arası tekrar kullanımı kontrol edilir.
- Personel moderasyon ekranına riskli hesaplar, otomatik risk olayları ve kullanıcı şikâyetleri eklendi.
- Risk sinyalleri otomatik hesap kapatma veya ceza uygulamaz; bütün sonuçlar personel incelemesine bırakılır.
- Kullanıcı veri ihracına gönderilmiş kullanıcı ve ilan şikâyetleri eklendi; alınan şikâyetlerin üçüncü taraf ayrıntıları gizli tutuldu.
- Eski veritabanları için güvenlik tablolarını ve görsel parmak izi alanını tamamlayan geriye uyumlu şema komutu eklendi.
- Codespaces, üretim başlangıcı ve GitHub Actions akışına şema doğrulama ve fotoğraf parmak izi tamamlama adımları eklendi.

## v1.17.0 — Kayıtlı aramalar ve akıllı ilan bildirimleri

- Kayıtlı aramalara Anlık, Günlük özet ve Kapalı bildirim sıklığı eklendi.
- Aynı arama–ilan çifti için tekrar bildirim üretilmesini engelleyen `SavedSearchMatch` modeli eklendi.
- Yeni ilan yayınlandığında anlık arama eşleşmeleri; bakım komutunda günlük toplu özetler üretilir.
- Liste ekranı ve bildirim görevi ortak filtre motoruna bağlandı; eksik kategori, teslimat, araç, emlak, takip ve fiyat düşüşü filtreleri düzeltildi.
- Kayıtlı arama düzenleme, kopya engelleme, güvenli parametre beyaz listesi ve kullanıcı başına sınır eklendi.
- v1.16.0 yakınlık keşfi kümülatif pakete dahil edildi; konum izninde mesafe, izin reddinde şehir–ilçe yedeği kullanılır.
- PWA özel sayfa listesi ve robots kuralları kayıtlı aramalar/favoriler için sıkılaştırıldı.
- Yeni model ve alanlar nedeniyle migration gerekir.

## v1.16.0 — Yakındaki ilanlar ve konum tabanlı keşif

- Ana sayfa ve ilan sonuçlarına Yakınımda düğmesi eklendi.
- Koordinatlı ilanlar seçilen yarıçapta kesin mesafeyle filtrelenir ve sıralanır.
- İlan kartlarında yaklaşık kilometre gösterimi eklendi.
- Konum izni reddedildiğinde profil veya seçili şehir–ilçe filtresine dönülür.
- Anlık koordinatlar kullanıcı profiline veya konum geçmişine kaydedilmez.

## v1.15.0 — Güvenli mesajlaşma ve dolandırıcılık uyarısı

- Mesajlara yerel ve açıklanabilir risk analizi eklendi.
- Şifre/doğrulama kodu, kimlik-kart görüntüsü, uzaktan erişim, ön ödeme, acele baskısı, kısaltılmış bağlantı, alternatif ödeme ve platform dışı iletişim sinyalleri taranır.
- Yüksek/kritik riskli mesajlarda ikinci onay zorunlu hale getirildi; metin ilan detayında korunarak yeniden gösterilir.
- Mesaj alıcısı risk seviyesini, gerekçeleri ve güvenli davranış önerisini konuşma içinde görür.
- Riskli mesaj bildirimlerinde şüpheli içerik bildirim gövdesinde tekrar edilmez.
- Güvenlik ön izlemesi, karakter sayacı, mobil tasarım ve destek bağlantısı eklendi.
- Güvenli mesaj, riskli mesaj, onaylı gönderim ve bildirim önizlemesi için regresyon testleri eklendi.
- Veritabanı migration gerektirmez; akıllı eşleştirme, fiyat rehberi ve Gemini akışı korunur.

## v1.14.1.1 — Emlak fiyat rehberi hata düzeltmesi

- Alt kategorideki emlak ilanı için yakın kategori fiyatlarını ararken oluşan `FieldError` düzeltildi.
- Kategori kök filtresi her durumda Django `Q` nesnesi olarak uygulanır.
- Eski sözlük biçimli kök filtrelerine karşı savunmalı uyumluluk eklendi.
- `demo-emlak` benzeri ilan detaylarının HTTP 500 vermesini önleyen regresyon testi eklendi.
- Akıllı eşleştirme, mobil sistem ve Gemini ilan asistanı değiştirilmedi.


## v1.14.0 — Arıyorum–Satıyorum akıllı eşleştirme

- Arıyorum, hizmet arıyorum ve iş arıyorum ilanları için açıklanabilir 0–100 eşleşme puanı eklendi.
- Kategori, ilan türü, ortak kelimeler, marka/model, şehir/ilçe, bütçe ve teslim uyumu birlikte değerlendirilir.
- Arayan kullanıcılar ve ilan sahipleri için iki sekmeli Akıllı Eşleşmeler merkezi eklendi.
- Yeni eşleşmeler iki tarafa da uygulama içi bildirim gönderebilir; bildirim tercihleri ayrı ayrı yönetilebilir.
- Kullanıcıların eşleşmeleri kendi tarafında gizleyebilmesi sağlandı.
- Engellenen kullanıcılar, süresi dolmuş ve yayında olmayan ilanlar eşleşme dışında bırakıldı.
- Açıkça farklı marka/model taşıyan yanlış sonuçlar elendi; ilan değişince geçersiz eski eşleşmeler otomatik temizlenir.
- Mevcut ilanları tarayan `rebuild_listing_matches` bakım komutu eklendi.
- Demo verilerine çalışan telefon arama/satış eşleşmesi eklendi.
- Eşleşme merkezi mobil denetim rotalarına, PWA varlıklarına ve GitHub Actions doğrulamasına dahil edildi.
- `ListingMatch` modeli ve eşleşme bildirim tercihleri nedeniyle migration oluşur.

## v1.13.2 — Site geneli mobil sistem ve otomatik denetim

- Mobil iyileştirme yalnız ilan sayfalarından çıkarılarak hesap, giriş, profil, mesaj, teklif, bildirim, destek, işlem, Tam Yönetim, Kazanç Ağı ve personel ekranlarına yayıldı.
- Ortak form alanları, kartlar, başlıklar, butonlar ve yatay kaydırılabilir alanlar 360–430 piksel telefon ekranlarına uyarlandı.
- Mesaj listesi, destek kuyruğu ve hesap panelinde bilgi hiyerarşisi ve tek elle kullanım güçlendirildi.
- Site genelindeki fiyat gösterimleri Türkçe binlik ayırıcıyla tutarlı hâle getirildi.
- `v132-mobile-system.css` ve `v132-mobile-system.js` eklendi.
- Gerçek Chromium üzerinde 360, 390 ve 430 piksel ekran görüntüsü, yatay taşma, tarayıcı hatası ve dokunma hedefi raporu üreten Playwright denetimi eklendi.
- Ana test workflow'una bağımlılıksız mobil sözleşme kontrolü eklendi; görsel denetim ayrı ve engelleyici olmayan workflow olarak çalışır.
- PWA önbelleği `ilansehri-v1132` olarak yenilendi.
- Gemini sağlayıcısı ve veritabanı modelleri değiştirilmedi; migration yoktur.

## v1.13.1 — Mobil keşif ve ilan bilgi akışı

- Mobil hızlı filtreler, sonuç özeti ve ilan türüne duyarlı filtre alanları eklendi.
- İlan kartlarında yerel fiyat gruplaması ve kategori rozeti güçlendirildi.
- İlan detayında temel özellikler ve satıcı özeti mobilde öne taşındı.
- Mobil arama temizleme düğmesi ve alt menü sayaçları eklendi.

## v1.13.0.1 — Mobil fiyat biçimlendirme düzeltmesi

- Mobil ilan detayındaki fiyat özeti Türkçe binlik ayırıcıyla gösterilir.
- `12500 TL` yerine `12.500 TL` biçimi kullanılır.
- İlan detayındaki ana fiyat, eski fiyat, fiyat geçmişi ve bekleyen teklif tutarları aynı biçime getirildi.
- Mobil deneyim ve Gemini ilan asistanı değiştirilmedi.
- Yeni migration yoktur.

# v1.13.0 — Mobil İlan Odaklı Deneyim

- Masaüstü görünümü korunurken 780 piksel ve altında ayrı mobil tasarım katmanı eklendi.
- Mobil üst alana hızlı ilan araması ve sayfaya göre akıllı görünürlük eklendi.
- Alt navigasyon tek elle kullanım, güvenli alan ve aktif sayfa vurgusuyla güçlendirildi.
- Ana sayfa mobilde daha kısa kahraman alanı, yatay kategori şeridi ve ilan akışına daha erken erişim sunuyor.
- İlan sonuçlarında kompakt liste mobil varsayılanı oldu; kart yazıları, fiyat, konum ve fotoğraf dengesi iyileştirildi.
- Filtre paneli soldan gelen dar menü yerine alttan açılan, büyük dokunma alanlı mobil sayfaya dönüştürüldü.
- İlan detayında fiyat özeti fotoğraf galerisinden önce gösteriliyor; galeri, detay sekmeleri ve sabit iletişim çubuğu yenilendi.
- İlan verme sihirbazında mobil önizleme kaldırıldı, adımlar yataylaştırıldı, alanlar ve alt işlem düğmeleri büyütüldü.
- Mobil ve masaüstü ilan görünümü tercihleri ayrı saklanıyor; masaüstü tercihi mobil seçimden etkilenmiyor.
- Yeni CSS/JavaScript dosyaları PWA önbelleğine eklendi; cache sürümü `ilansehri-v1130` olarak yenilendi.
- Model veya veritabanı değişikliği yapılmadı; migration gerektirmez.

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
