# İlan Şehri v1.23 detay deneyimi

## Amaç
İlanı inceleyen kullanıcının fotoğrafları rahat gezebilmesi, fiyat ve konumu hızlı anlaması, satıcı güvenini tek yerde görebilmesi ve mobilde mesaj/teklif işlemlerine kolay ulaşması.

## Galeri sözleşmesi
- `data-v123-gallery`: ana galeri kabı
- `data-v123-gallery-thumb`: fotoğraf seçicileri
- `data-v123-gallery-prev` / `data-v123-gallery-next`: yön düğmeleri
- Klavye: sol/sağ ok, Enter, boşluk ve Escape
- Dokunmatik: yatay kaydırma
- Işık kutusu: `role="dialog"`, `aria-modal="true"`

## Alıcı deneyimi
- Fiyat ve işlem türü özeti
- Satıcı üyelik süresi, işlem sayısı, aktif ilan sayısı ve doğrulama rozetleri
- Güvenli işlem uyarısı
- Mobil fiyat, mesaj ve teklif çubuğu
- Kategori ve konum öncelikli benzer ilanlar

## Veri ve güvenlik
- Yeni tablo veya model alanı eklenmez.
- Açık adres gösterilmez.
- Mesaj ve teklif izinleri mevcut engelleme, oturum ve oran sınırı kurallarını kullanır.
