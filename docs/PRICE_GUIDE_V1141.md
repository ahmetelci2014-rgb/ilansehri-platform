# v1.14.1 Akıllı Fiyat Rehberi

Akıllı Fiyat Rehberi, İlan Şehri içindeki yayında olan ve fiyatı bulunan benzer ilanları karşılaştırır. Sistem dış piyasa verisi, ekspertiz veya satış garantisi kullanmaz.

## Desteklenen ilanlar

- Ürün / eşya: kategori, marka, model ve şehir
- Araç: kategori, marka, model, yakın model yılı ve kilometre
- Emlak: işlem türü, kategori, şehir, ilçe/mahalle, oda sayısı ve yakın metrekare

Satılık ve kiralık dışındaki işlemlerde fiyat rehberi çalışmaz. Hizmet, iş ve “Arıyorum” ilanlarında tahmin üretilmez.

## Güvenlik ve dayanıklılık

- Yalnız yayındaki, süresi dolmamış ve fiyatı bulunan ilanlar kullanılır.
- İlan sahibinin kendi diğer ilanları karşılaştırmaya alınmaz.
- En az dört veya beş anlamlı benzer ilan bulunmadan sonuç gösterilmez.
- Aşırı uç fiyatlar çeyrekler arası açıklık yöntemiyle çıkarılır.
- Sonuçta örnek sayısı, güven seviyesi ve kullanılan karşılaştırma ölçütü gösterilir.
- Rehber fiyat alanını kendiliğinden değiştirmez; kullanıcı “Orta değeri fiyat alanına yaz” düğmesine açıkça basmalıdır.

## Kullanıcı sonucu

- Tahmini fiyat aralığı
- Benzer ilanların orta değeri
- Piyasanın altında / piyasa aralığında / piyasanın üzerinde etiketi
- Karşılaştırılan ilan sayısı
- Düşük, orta veya yüksek veri güveni
- Hesaplama ölçütleri ve çıkarılan uç fiyat sayısı
