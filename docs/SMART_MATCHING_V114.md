# v1.14 Arıyorum–Satıyorum Akıllı Eşleştirme

## Amaç

İlan Şehri'nde `Arıyorum`, `Hizmet Arıyorum` ve `İş Arıyorum` ilanlarını uygun satış, kiralama, takas, hizmet veya iş ilanlarıyla otomatik olarak buluşturur.

## Eşleşme puanı

Sistem dış yapay zekâ servisine ihtiyaç duymadan açıklanabilir bir puan üretir. Puan şu sinyallerden oluşur:

- İlan ve işlem türü uyumu
- Aynı kategori veya aynı ana kategori
- Başlık, açıklama, etiket ve teknik özelliklerde ortak kelimeler
- Marka ve model yakınlığı
- Şehir ve ilçe uyumu
- Arayan ilandaki bütçe ile sunulan fiyatın yakınlığı
- Teslim şekli uyumu

50 puanın altındaki sonuçlar kullanıcıya gösterilmez. Puan 100 ile sınırlandırılır.
Açıkça farklı marka veya model bilgileri yanlış eşleşmeyi engeller. İlan başlığı, kategori ya da marka/model değiştiğinde artık geçerli olmayan eski eşleşmeler temizlenir.

## Güvenlik ve gizlilik

- Kullanıcı kendi ilanıyla eşleştirilmez.
- Birbirini engelleyen kullanıcıların ilanları eşleştirilmez.
- Yalnız aktif ve yayındaki ilanlar sonuçlara girer.
- Kullanıcının adı eşleşme kartında doğrudan açığa çıkarılmaz; iletişim ilan sayfasındaki mevcut güvenlik akışından başlar.
- Her kullanıcı eşleşmeyi yalnız kendi tarafında gizleyebilir.

## Bildirimler

Yeni bir eşleşme oluştuğunda arayan ve ilan sahibi uygulama içi bildirim alabilir. Bildirim tercihleri ekranından akıllı eşleşme bildirimleri kapatılabilir. Doğrulanmış e-posta adresi bulunan kullanıcılar ayrıca e-posta seçeneğini açabilir.

## İşletim

Mevcut ilanları yeniden taramak için:

```bash
python manage.py rebuild_listing_matches
```

Bildirim de üretmek için:

```bash
python manage.py rebuild_listing_matches --notify
```

Codespaces başlangıcında ilk 500 yayındaki ilan sessiz biçimde yeniden taranır.
