# Bildirim ve Moderasyon Operasyonu

## Bildirim tercihleri

Kullanıcılar `/hesap/bildirim-tercihleri/` ekranından isteğe bağlı uygulama içi bildirimleri, anlık e-posta bildirimlerini ve günlük/haftalık özet sıklığını yönetir.

İşlem, teslim, ilan moderasyonu, doğrulama, destek ve önemli sistem bildirimleri hesap güvenliği nedeniyle uygulama içinde her zaman gösterilir.

Anlık e-posta gönderimi Django e-posta ayarlarını kullanır. Canlı ortamda SMTP bilgileri `.env` içinde tanımlanmalıdır.

## Bildirim özetleri

```bash
python manage.py send_notification_digests
```

Komut, günlük veya haftalık özet seçen kullanıcılara son dönem bildirimlerini gönderir. Anlık e-posta olarak zaten seçilen türler özette tekrar edilmez.

Canlı sunucuda bu komutun saatlik veya günlük zamanlanmış görev olarak çalıştırılması gerekir. Kullanıcının seçtiği süre dolmadıysa yeni özet gönderilmez.

## Toplu moderasyon

`/ilanlar/moderasyon/` ekranı şu filtreleri sunar:

- İlan, açıklama veya kullanıcı araması
- İlan türü
- Şehir
- Kalite puanı
- En eski / en yeni sıralaması

Personel aynı anda en fazla 100 inceleme kaydı seçerek onaylayabilir veya ortak açıklamayla düzeltme isteyebilir. Her ilan işlemi `StaffActionLog` tablosuna ayrı ayrı kaydedilir.

Düzeltme isteğinde açıklama zorunludur. Kuyruktan daha önce çıkarılmış ilanlar toplu işlem sırasında atlanır.
