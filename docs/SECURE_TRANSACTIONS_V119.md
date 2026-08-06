# İlan Şehri v1.19.0 — Güvenli İşlem ve Kör Değerlendirme

## İşlem akışı

1. Gerçek bir teklif kabul edilir ve alıcı–satıcıya bağlı tek işlem kaydı açılır.
2. Teslim aşamasını yalnız satıcı başlatır.
3. Elden veya yerinde teslimde alıcı, ürün/hizmet yanındayken 6 haneli kod oluşturur.
4. Kod 15 dakika geçerlidir ve beş hatalı denemeden sonra yenilenmelidir.
5. Satıcı kodu doğrulayınca satıcı onayı kaydedilir; alıcı kontrol sonrası kendi onayını verir.
6. Kargo/dijital teslimde taraflar teslim aşamasında ayrı ayrı onay verir.
7. İki onay tamamlanınca ilan sonuçlanır ve değerlendirme penceresi açılır.

## Kod güvenliği

- Açık teslim kodu yalnız alıcıya tek seferlik Django mesajı olarak gösterilir.
- Veritabanında yalnız Django parola hash'i saklanır.
- Kod işlem olayı notuna, bildirime veya yönetim ekranına yazılmaz.
- Kod doğrulandığında hash temizlenir.

## Kör değerlendirme

- İlk değerlendirme kullanıcı profilinde görünmez ve güven puanına katılmaz.
- İkinci taraf da değerlendirirse iki yorum aynı anda yayınlanır.
- İkinci taraf yazmazsa ilk yorum 7 gün sonra günlük bakım komutunda yayınlanır.
- Yalnız tamamlanmış işlemin gerçek tarafları 30 gün içinde değerlendirme yapabilir.
- Aynı kullanıcı aynı işlem için yalnız bir değerlendirme gönderebilir.

## Sınırlar

Bu sistem ödeme veya emanet para hizmeti değildir. Teslim kodu yalnız yüz yüze teslim adımını kayıt altına alır; para transferini doğrulamaz.
