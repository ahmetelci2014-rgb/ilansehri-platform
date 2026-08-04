# İlan Şehri Destek Operasyonu

## Kullanıcı akışı

1. Kullanıcı Yardım Merkezi'nde hazır cevap arar.
2. Cevap yeterli değilse hesapla giriş yaparak destek talebi açar.
3. Talep bir ilan veya işlem kaydıyla ilişkilendirilebilir.
4. Kullanıcı gelen yanıtı Bildirimler ve Taleplerim ekranından görür.
5. Kullanıcı yeni yanıt gönderebilir veya talebi kapatabilir.

## Personel akışı

1. Personel `/yardim/ekip/` kuyruğunda açık talepleri görür.
2. Talebi kendine veya başka aktif personele atar.
3. Öncelik ve durum belirler.
4. Kullanıcıya açık yanıt veya ekip içi not ekler.
5. Tüm hareketler personel işlem günlüğüne yazılır.

## Durumlar

- Yeni
- İnceleniyor
- Kullanıcı yanıtı bekleniyor
- Çözüldü
- Kapatıldı

## Güvenlik

- Kullanıcı başka bir kullanıcının destek talebine erişemez.
- Ekip içi notlar kullanıcı sorgularında filtrelenir.
- Talep ve yanıt gönderiminde temel hız sınırı vardır.
- Destek ve ekip sayfaları PWA önbelleğine alınmaz.
