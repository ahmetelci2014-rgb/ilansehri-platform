# v1.21 kategori, filtre, konum ve mobil keşif

## Amaç

İlan Şehri'nin ana kullanım yolunu yeni yan modüllerle büyütmek yerine ilan bulma ve ilan verme deneyimini güçlendirir. Öncelik sırası kategori, filtre, konum, mobil kullanım ve fotoğraf kalitesidir.

## Kategori sözleşmesi

- Kök kategoriler ilan türleriyle eşlenir: Ürün & Eşya, Araç, Emlak, Hizmet, İş ve İhtiyaçlar.
- İlan oluştururken kullanıcı kök kategori yerine uygun alt kategoriyi seçer.
- Seçilen kategori ile ilan türü uyuşmuyorsa form yayınlamaya izin vermez.
- Arama ekranında kök kategori seçildiğinde bütün aktif alt kategoriler birlikte aranır.
- `seed_categories` komutu mevcut kayıtları silmeden profesyonel alt kategori kataloğunu günceller.

## Filtre sözleşmesi

Liste ekranı ve kayıtlı aramalar aynı filtre motorunu kullanır. Mahalle, renk, ısıtma, kat, hizmet bölgesi, deneyim ve azami bina yaşı filtreleri de bu ortak sözleşmeye dahildir. Aktif filtreler tek tek kaldırılabilir ve kategoriye göre ilgili ayrıntı alanları gösterilir.

## Konum sözleşmesi

- 81 şehir seçimde bulunur.
- Katalogdaki ilçe ve mahalleler bağlı öneri olarak gösterilir.
- Katalogda olmayan yerler serbestçe yazılabilir.
- Yayındaki ilanlarda kullanılan geçerli ilçe ve mahalleler öneri servisine eklenir; böylece katalog gerçek pazar verisiyle kendini tamamlar.
- Yakınımda filtresi mevcut koordinat tabanlı davranışını korur.

## Mobil keşif

- Filtreler telefonlarda alttan açılan panel olarak çalışır.
- Şehir ve ilçe ana aramada görünür; mahalle ayrıntısı filtre panelinde korunur.
- Popüler alt kategoriler yatay, tek elle kullanılabilir kısayollar şeklinde sunulur.
- Aktif filtreler kaydırılabilir etiketler olarak görünür.
- Sonuç başlığı ve konum özeti kullanıcının seçimini açıkça anlatır.

## Fotoğraf kalitesi

Yeni fotoğraflar yüklenmeden önce sıralanabilir ve kaldırılabilir. İlk fotoğraf kapak adayıdır. Tarayıcı çözünürlüğü kontrol eder; 900×700 piksel altındaki görseller için uyarı verir. Bu uyarı yayınlamayı engellemez, kullanıcıyı daha kaliteli görsele yönlendirir.

## Yardımcı modüllerin konumu

Randevu sistemi yalnız aktif davet olduğunda ana başlıkta görünür. İlan hazırlama desteği ve görev ortağı alanı hesap içindeki ikincil hizmetler olarak korunur; ana ilan keşfinin önüne geçmez.
