# İlan Şehri v1.25 İletişim Merkezi

## Amaç

Mesajlaşma, teklif ve güvenli işlem devamlılığını farklı ekranlarda kaybolmadan tek kullanıcı akışında birleştirmek.

## Mesaj kutusu

- `İşlem bekleyen`: okunmamış mesajlar ile yanıt sırası kullanıcıda olan teklifleri birleştirir.
- `Okunmamış`: yalnız karşı taraftan gelen ve henüz okunmamış mesajları gösterir.
- `Alış görüşmeleri` ve `Satış görüşmeleri`: kullanıcının görüşmedeki rolüne göre ayrılır.
- `Arşiv`: alıcı ve satıcı için bağımsızdır; diğer tarafın mesaj kutusunu etkilemez.
- Arama; ilan başlığı, kullanıcı adı ve ad-soyad üzerinde çalışır.

## Görüşme ekranı

- Son 120 mesaj hızlı yüklenir; kullanıcı gerektiğinde 500 mesaja kadar geçmişi açabilir.
- Tarih ayraçları, okundu bilgisi, görsel mesajlar ve mevcut güvenlik analizi korunur.
- Hazır yanıt düğmeleri yalnız mesaj alanını doldurur; kullanıcı onayı olmadan mesaj göndermez.
- Yeni mesaj iki taraftaki arşiv durumunu kaldırarak görüşmeyi tekrar aktif kutuya taşır.
- Mesaj gönderimi kullanıcı/IP hız sınırı ve engellenen kullanıcı kontrolünden geçer.

## Teklif devamlılığı

- Yalnız görüşmenin alıcısı, yayındaki ilan için görüşme içinden teklif oluşturabilir.
- Aynı ilan ve alıcı için bekleyen ikinci teklif oluşturulamaz.
- Teklif, olay geçmişi ve satıcı bildirimi birlikte kaydedilir.
- Görüşme ekranı mevcut teklifin tutarını, durumunu ve yanıt sırasını gösterir.
- Teklif Merkezi ilgili görüşmeye geri bağlantı verir ve bildirimden gelen odak kaybolmaz.

## Güvenlik sınırları

- Konuşmayı yalnız alıcı ve satıcı açabilir.
- Teklifi yalnız görüşmenin alıcısı başlatabilir.
- Engellenen kullanıcılar arasında mesaj ve teklif işlemi yapılmaz.
- Güvenli `next` dönüşü yalnız aynı sunucu içindeki adreslere izin verir.
- Randevu formu ana iletişim akışında zorunlu değildir; ikincil araç olarak korunur.

## Veritabanı

v1.25.0 yeni tablo veya model alanı eklemez. Migration gerekmez.
