# İlan Şehri v1.4 — Tasarım Dengeleme ve Responsive Kalite Turu

## Düzeltilenler

- Masaüstü, tablet ve mobil ekranlarda yatay taşma ve içerik kaymaları azaltıldı.
- Üst menü farklı ekran genişliklerinde kademeli ve dengeli biçimde sadeleştirildi.
- Ana sayfa arama, kategori, istatistik ve ilan bölümlerinin hizaları düzeltildi.
- İlan kartlarında eşit yükseklik, fiyat/başlık/spec alanı ve rozet çakışmaları düzenlendi.
- Listeleme ekranında filtre, sonuç başlığı, sıralama ve mobil filtre çekmecesi dengelendi.
- İlan detayında galeri, sabit yan panel, özellik tablosu ve mobil iletişim çubuğu düzeltildi.
- Teklif merkezi, karşı teklif penceresi ve zaman çizelgesi mobil uyumlu hale getirildi.
- Mesaj kutusu ve konuşma ekranında uzun başlık, taşma ve yan panel kaymaları giderildi.
- Satıcı profili, hesap ekranları, formlar, bildirimler ve yönetim merkezi responsive hale getirildi.
- Çok küçük metinler okunabilir seviyeye yükseltildi.
- Mobil alt menü ve sabit iletişim alanlarına güvenli ekran boşluğu eklendi.
- Mobil menü bağlantı seçilince, Escape tuşunda veya masaüstüne geçince otomatik kapanır.
- Hareket azaltma tercihi olan kullanıcılar için animasyonlar sınırlandı.

## Teknik yaklaşım

- İş mantığı ve veritabanı modelleri değiştirilmedi.
- Bütün düzeltmeler geri alınabilir ayrı `static/css/v14-polish.css` katmanında tutuldu.
- Mevcut v1.3 pazarlık, fiyat takibi, satıcı takibi ve bildirim özellikleri korundu.
