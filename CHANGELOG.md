# İlan Şehri v1.5 — Keşif ve Kullanıcı Deneyimi

- Kategori bazlı profesyonel vitrin sayfaları eklendi.
- Başlık, kategori, marka ve ilan sonuçlarını gösteren canlı arama önerileri eklendi.
- Kayıtlı aramalar için ayrı yönetim ekranı ve bildirim aç/kapat akışı eklendi.
- İlan sonuçlarında tek adımda “Aramayı kaydet” alanı eklendi.
- Bildirim Merkezi tür ve okunma durumuna göre filtrelenebilir hale getirildi.
- İlan verme ekranına ilerleme göstergesi ve canlı ilan önizlemesi eklendi.
- Sayfalama sorgularındaki yinelenen `page` parametresi düzeltildi.
- Yeni özelliklere ait erişim ve filtre testleri eklendi.

# Değişiklik Günlüğü

## v1.3 — Pazarlık, Fiyat Takibi ve Satıcı Ağı

- Teklif merkezi yenilendi; gönderilen ve alınan teklifler tek ekranda durumlarına göre yönetilebilir hale getirildi.
- Alıcı ve satıcının sırayla karşı teklif verebildiği gerçek pazarlık akışı eklendi.
- İlk teklif, karşı teklifler, kabul, ret ve geri çekme adımları zaman çizelgesinde saklanmaya başlandı.
- Karşı teklif yalnız sırası gelen kullanıcı tarafından yapılabilir; üçüncü kişilerin erişimi engellendi.
- Fiyat geçmişi modeli, eski fiyat gösterimi, indirim yüzdesi ve fiyatı düşen ilan akışları eklendi.
- Favoriye alınan ilanın fiyatı düştüğünde kullanıcıya bildirim gönderilmesi eklendi.
- Moderasyondaki fiyat değişiklikleri için bildirim yalnız ilan yeniden onaylandığında ve tek kez gönderilecek şekilde güvenli hale getirildi.
- Satıcı takip etme, takipten çıkma, takipçi sayıları ve takip edilen satıcıların ilan akışı eklendi.
- Takip edilen satıcı yeni ilan yayınladığında bildirim oluşturulması eklendi.
- Mesaj kutusuna okunmamış, alış ve satış görüşmesi filtreleri ile kullanıcı/ilan araması eklendi.
- Mesaj ekranı ilan özeti, karşı taraf güven bilgisi, görsel gönderme, arşivleme ve engelleme kontrolleriyle yenilendi.
- Ana sayfaya takip edilen satıcılar ve fiyatı düşen ilanlar bölümleri eklendi.
- İlan filtrelerine fiyat düşüşü ve takip edilen satıcı seçenekleri eklendi.
- Teklif pazarlığı, fiyat bildirimi, takip sistemi ve yetki kontrolleri için yeni otomatik testler eklendi.

## v1.2 — Profesyonel Marketplace

- Ana sayfa; konuma göre yeni ilanlar, popüler ilanlar, araç, emlak, hizmet ve son görüntülenenler bölümleriyle zenginleştirildi.
- İlan kartlarına satıcı doğrulaması, değerlendirme, fotoğraf sayısı, kategoriye özel kısa bilgiler, gerçek favori durumu ve karşılaştırma düğmesi eklendi.
- Aynı türde en fazla dört ilanı yan yana inceleyen oturum tabanlı karşılaştırma sistemi eklendi.
- İlan listeleme filtrelerine kategori, ürün durumu, teslimat, model yılı, kilometre, yakıt, vites, oda ve metrekare alanları eklendi.
- Mobil filtre çekmecesi, aktif filtre etiketleri ve karşılaştırma kısayolu eklendi.
- İlan detayına büyütülebilir galeri, satıcı güven puanı, değerlendirmeler, benzer ilanlar ve satıcının diğer ilanları eklendi.
- Son görüntülenen ilanlar oturumda saklanarak ana sayfada gösterilmeye başlandı.
- Favoriler sayfasındaki eski kart yapısı kaldırılarak marketplace kartlarıyla birleştirildi.
- Django teknik admininden ayrı profesyonel yönetim merkezi eklendi.
- Yönetim merkezinde ilan, kullanıcı, şikâyet, işlem, Tam Yönetim ve Kazanç Ağı göstergeleri bir araya getirildi.
- Karşılaştırma, son görüntüleme, favoriler ve yönetim merkezi için otomatik testler eklendi.
- v1.0.2 yorum URL sırası düzeltmesi korunmuştur.

## v1.1 — Marketplace dönüşümü

- Ana sayfa ilan odaklı gerçek pazar yeri düzenine geçirildi.
- Yoğun fotoğraflı ilan kartları ve mobil iki sütunlu akış eklendi.
- Arama, konum ve kategoriler ilk ekrana taşındı.
- İlan listeleme ekranı profesyonel filtreli katalog olarak yenilendi.
- İlan detayı büyük galeri, satıcı kartı, favori, mesaj ve teklif odaklı yenilendi.
- Kurumsal tanıtım blokları ana sayfadan kaldırıldı.
- Üst menü ve mobil alt navigasyon marketplace kullanımına göre sadeleştirildi.

## v1.0 — Tamamlanmış MVP

- Profil, doğrulama, güven puanı, ilan, mesajlaşma, teklif, işlem, yorum, moderasyon, Tam Yönetim ve Kazanç Ağı modülleri tamamlandı.
- PWA, Docker/PostgreSQL/Gunicorn/WhiteNoise hazırlığı ve GitHub Actions kontrolleri eklendi.

## v0.6

- Türkiye konum seçimleri, kategoriye özel alanlar, bildirim merkezi ve moderasyon eklendi.

## v0.5

- İlan yönetimi, favoriler ve özel mesajlaşma eklendi.
