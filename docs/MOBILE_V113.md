# İlan Şehri v1.13.0 — Mobil İlan Odaklı Deneyim

Bu sürüm masaüstü tasarımını değiştirmeden, `780px` ve altındaki ekranlarda ayrı bir mobil deneyim katmanı uygular.

## Mobil ana sayfa

- Üst alanda sürekli erişilebilir hızlı ilan araması
- Daha kısa tanıtım alanı ve ilanlara daha erken erişim
- Yatay kategori seçimi
- Okunabilir ilan kartları ve daha büyük dokunma alanları
- Tek elle kullanılabilen sabit alt navigasyon

## İlan listesi

- Mobilde varsayılan kompakt ilan akışı
- Mobil ve masaüstü görünüm tercihlerinin ayrı saklanması
- Fiyat, başlık, konum ve temel özelliklerin daha rahat taranması
- Alttan açılan filtre sayfası
- Aktif filtre sayısının filtre düğmesinde gösterilmesi
- Dar ekranlarda karşılaştırma düğmesinin kartlardan kaldırılarak ekran karmaşasının azaltılması

## İlan detayı

- Fiyat ve konum özeti fotoğraf galerisinden önce
- Kenardan kenara fotoğraf galerisi
- Yatay ve sabit ayrıntı sekmeleri
- Mesaj ve teklif işlemleri için sabit alt iletişim alanı

## İlan verme

- Mobilde gereksiz canlı önizlemenin gizlenmesi
- Fotoğraf yükleme ve AI hızlı başlangıç alanının sadeleştirilmesi
- Adımların yatay kaydırılabilir hâle getirilmesi
- iOS yakınlaştırmasını önlemek için 16px form alanları
- Büyük ve güvenli dokunma hedefleri
- Alt navigasyonun üzerinde sabit işlem düğmeleri

## Teknik notlar

- Yeni dosyalar: `static/css/v113-mobile-market.css`, `static/js/v113-mobile-market.js`
- PWA cache adı: `ilansehri-v1130`
- Model ve migration değişikliği yoktur.
- Masaüstü kuralları korunur; yeni tasarım yalnız mobil medya sorgularında devreye girer.


## v1.13.1 ek geliştirmeleri

- Hızlı ilan filtreleri ve mobil sonuç özeti
- İlan türüne duyarlı filtre alanları
- Mobil kart kategori rozeti ve yerel fiyat gruplaması
- Detay sayfasında temel özellikler ve satıcı özeti
- Mobil arama temizleme düğmesi ve alt menü sayaçları
- PWA cache: `ilansehri-v1131`
