# Değişiklik Günlüğü

## v1.25.1 — Mobil, tablet ve masaüstü stabilizasyonu

- Mobil görüşme ekranında daha önce gizlenen görsel mesaj yükleme alanı yeniden kullanılabilir hale getirildi.
- Mobil sabit mesaj yazma alanının alt navigasyon ve güvenli ekran boşluklarıyla çakışması giderildi.
- 781–1100 px tablet genişliklerinde üst arama, menü ve navigasyon geçişleri düzenlendi.
- 900 px ilan sonuç ekranındaki sonuç araçlarının yatay taşması giderildi.
- Destek Operasyonu ekip tablosunun tablet ekranında ana sayfayı yatay taşırması engellendi.
- Mobil Görsel Denetim korunurken 900, 1024, 1280 ve 1440 px genişlikleri kapsayan ayrı Tablet ve Masaüstü Görsel Denetim eklendi.
- Yeni responsive denetim 160/160 ekran kombinasyonunu başarıyla doğrular.
- Yeni tablo veya model alanı eklenmedi; veritabanı migration işlemi gerekmez.

## v1.25.0 — Mesajlaşma, teklif ve iletişim merkezi

- Mesaj kutusuna işlem bekleyen, okunmamış, alış, satış ve arşiv görünümleri eklendi.
- Okunmamış mesajlarla kullanıcının yanıtını bekleyen teklifler tek “İşlem bekleyen” sayacında birleştirildi.
- Görüşmeler ilan başlığı, kullanıcı adı ve ad-soyad bilgisiyle aranabilir hale getirildi.
- Konuşmalar alıcı ve satıcı için bağımsız arşivlenebilir ve yeniden mesaj kutusuna taşınabilir hale getirildi.
- Görüşme ekranına tarih ayraçları, hızlı yanıtlar, sabit mobil yazma alanı ve son 120 mesajı hızlı açan geçmiş yönetimi eklendi.
- Alıcının görüşme içinden teklif oluşturması; mevcut teklifin durumu ve yanıt sırasının aynı ekranda izlenmesi sağlandı.
- Teklif Merkezi gelen, gönderilen ve yanıt bekleyen yön filtreleri, durum sekmeleri, arama ve odaklanan teklif kartıyla yenilendi.
- Teklif kartları ilgili konuşmayla bağlandı; karşı teklif ve ret bildirimleri doğru teklif kartına yönlendirilir.
- Üst menü teklif rozeti bütün bekleyen teklifler yerine yalnız kullanıcının işlem yapması gereken teklifleri sayar.
- Randevu formu ana görüşme akışından çıkarılıp ikincil görüşme ve güvenlik araçları altına taşındı.
- Mesaj gönderme ve görüşme içi teklif oluşturma akışlarına hız sınırlaması ve mevcut engelleme kontrolleri bağlandı.
- Demo görüşmesine örnek mesaj geçmişi eklendi; Mobil Görsel Denetim alıcı ve satıcı iletişim ekranlarıyla 168 ekran kombinasyonuna genişletildi.
- Yeni tablo veya model alanı eklenmedi; veritabanı migration işlemi gerekmez.

## v1.24.0 — Satıcı Merkezi ve ilan yönetimi

- Kullanıcıya ait bütün ilanları ayrı bir Satıcı Merkezi'nde listeleyen `/ilanlar/ilanlarim/` ekranı eklendi.
- İlanlar yayın durumu, metin araması ve görüntülenme/favori/teklif/görüşme/süre sıralamasıyla yönetilebilir hale getirildi.
- Toplam görüntülenme, favori, görüşme, teklif, yayındaki ilan ve işlem bekleyen kayıt sayıları tek performans özetinde birleştirildi.
- İlan kartlarına kalite puanı, ilk geliştirme önerisi, yayın süresi, bekleyen teklif ve okunmamış mesaj bilgisi eklendi.
- En fazla 50 sahip olunan ilan için toplu duraklatma, yayınlama, 60 gün yenileme, sonuçlandırma ve taslağa alma akışı eklendi.
- Toplu işlemlerde başka kullanıcı ilanları sorgu seviyesinde dışlanır; inceleme veya ret durumundaki ilanların doğrudan yayınlanması korunur.
- Tekil ilan durum işlemleri güvenli `next` dönüşünü destekler; Satıcı Merkezi'ndeki filtre konumu kaybolmaz.
- Hesap paneli son altı ilana indirildi ve ayrıntılı yönetim bağlantıları Satıcı Merkezi'ne taşındı.
- Randevu alanı hesap ana akışında geri plana alındı; yalnız yaklaşan kayıt bulunduğunda gösterilir.
- Mobil Görsel Denetim satıcı ilan merkezi ve işlem bekleyen filtresiyle 156 ekran kombinasyonuna genişletildi.
- Yeni tablo veya model alanı eklenmedi; veritabanı migration işlemi gerekmez.

## v1.23.0 — İlan detay ve mobil alıcı deneyimi

- İlan galerisine ileri/geri düğmeleri, sayaç, dokunmatik kaydırma, klavye kontrolü ve erişilebilir büyütülmüş galeri eklendi.
- Satıcı güven özeti, mobil fiyat/mesaj/teklif çubuğu ve kategori/konum öncelikli benzer ilan sıralaması eklendi.
- Mobil Görsel Denetim ilan detayını ziyaretçi, alıcı ve satıcı rolleriyle 150 ekran kombinasyonunda doğrular.
- Yeni tablo veya model alanı eklenmedi.

## v1.22.0 — Mobil görsel düzen ve ilan kalitesi

- Ana sayfa kategori alanı, her ilan türü için en güçlü alt kategori kısayollarını gösteren profesyonel kategori merkezine dönüştürüldü.
- Ana sayfa aramasına ilçe alanı eklendi; giriş yapan kullanıcının şehir ve ilçe tercihi arama akışına taşındı.
- Görev ortağı sayacı ana vitrinden kaldırıldı; aktif şehir sayısı daha temel bir pazar göstergesi olarak öne çıkarıldı.
- İlan kartları kategori adı, pazarlık bilgisi, fotoğraf durumu, kategoriye özel özellikler, satıcı güveni ve mahalle bilgisiyle yeniden düzenlendi.
- Fotoğrafsız ilan kartları kategoriye uygun, açıklayıcı boş görsel durumu kullanır.
- İlan verme sihirbazına adım/kalite ilerleme çubuğu ve kategori, metin, fiyat, konum ve fotoğraf kontrol listesi eklendi.
- Codespaces başlangıç mesajı sabit sürüm yerine `VERSION` dosyasını kullanır.
- Mobil Görsel Denetim emlak ve hizmet kategori açılışlarıyla 144 ekran kombinasyonuna genişletildi.
- v1.22 statik varlıkları service worker önbelleğine, mobil sözleşme kontrolüne ve regresyon testlerine bağlandı.
- Veritabanı şema değişikliği yapılmadı.

## v1.21.0 — Kategori, filtre, konum ve mobil keşif

- Kök kategori slug'larını ilan türleriyle eşleyen ortak kategori sözleşmesi eklendi.
- İlan oluştururken ilan türüyle uyuşmayan veya alt kategori seçilmeden gönderilen kayıtlar engellendi.
- Profesyonel ürün, araç, emlak, hizmet, iş ve ihtiyaç alt kategori kataloğu genişletildi; mevcut kayıtlar silinmeden güncellenir.
- Kök kategori filtresi bütün aktif alt kategorileri kapsayacak şekilde düzeltildi.
- Mahalle, renk, ısıtma, kat, hizmet bölgesi, deneyim ve azami bina yaşı filtreleri liste ekranı ile kayıtlı aramalarda ortaklaştırıldı.
- Aktif filtreler kullanıcı dostu etiketlerle tek tek kaldırılabilir hale getirildi; sonuç başlığı ve konum özeti seçime göre yenilendi.
- Şehir–ilçe–mahalle öneri servisi statik katalogla birlikte yayındaki ilanlarda kullanılan konumları güvenli biçimde sunar.
- Mobil ilan sonuçları alttan açılan filtre paneli, popüler alt kategori kısayolları ve yatay aktif filtre şeridiyle yeniden düzenlendi.
- Yeni fotoğraflara yüklemeden önce sıralama, kaldırma, kapak adayı ve çözünürlük kalite uyarısı eklendi.
- Randevu yalnız bekleyen davet olduğunda ana başlıkta görünür; ilan desteği ve görev ortağı alanı ikincil hesap bağlantıları olarak korunur.
- Mobil Görsel Denetim konum ve kategori filtreli kamu ekranlarıyla 138 ekran kombinasyonuna genişletildi.
- Yeni kategori, filtre, konum ve form sözleşmeleri için regresyon testleri eklendi; veritabanı şema değişikliği gerekmez.

## v1.20.0 — Güvenli randevu ve teslim planlama

- İlan görüşmelerine yüz yüze, telefon, görüntülü ve teslim/hizmet randevusu önerme akışı eklendi.
- Randevular yalnız konuşmanın alıcı ve satıcısı tarafından görüntülenebilir ve yönetilebilir.
- Geçmiş veya 90 günden uzak tarih, eksik yüz yüze buluşma bilgisi ve aynı saat aralığındaki çakışmalar engellenir.
- Davet edilen kullanıcı için onay/ret; her iki taraf için aktif randevuyu iptal etme akışı eklendi.
- Yaklaşan 24 saat içindeki onaylı randevulara tek seferlik uygulama içi ve tercih edilirse e-posta hatırlatması gönderilir.
- Yanıt verilmeden tarihi geçen öneriler günlük bakım komutunda otomatik kapatılır.
- Randevu merkezi hesap paneline, mobil menüye, kişisel veri ihracına, Django Admin'e ve demo verilerine eklendi.
- `ensure_v120_schema` Codespaces, üretim ve iki GitHub Actions akışına eklendi.
- Mobil Görsel Denetim alıcı ve satıcı randevu ekranlarını da kapsayacak şekilde genişletildi.
- Sağlık yanıtı ve service worker önbellek sürümü doğrudan `VERSION` dosyasına bağlandı; gelecekteki sabit sürüm uyuşmazlıkları kaldırıldı.

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
