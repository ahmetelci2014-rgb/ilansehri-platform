# v1.15.0 Güvenli Mesajlaşma

## Amaç
İlan Şehri içindeki mesajlaşmada kullanıcıyı şüpheli ödeme, kimlik bilgisi, doğrulama kodu ve sahte bağlantı risklerine karşı işlem anında uyarmak.

## Çalışma şekli
1. Tarayıcı, kullanıcı yazarken yerel bir ön kontrol gösterir.
2. Sunucu aynı metni bağımsız ve kesin kurallarla tekrar analiz eder.
3. Orta riskte bilgilendirme görünür. Yüksek ve kritik riskte açık onay olmadan mesaj kaydedilmez.
4. Gönderilen riskli mesaj, alıcının konuşma ekranında gerekçeleriyle işaretlenir.
5. Bildirim gövdesi yüksek riskli mesaj içeriğini tekrar göstermez.

## Kontrol edilen sinyaller
- SMS/OTP/doğrulama kodu ve şifre talepleri
- Kimlik, banka kartı veya kart fotoğrafı talepleri
- AnyDesk, TeamViewer ve uzaktan erişim talepleri
- Kapora, havale, EFT ve ödeme bağlantısı baskısı
- Kısaltılmış bağlantılar
- Kripto ve hediye kartı gibi takibi zor ödeme yöntemleri
- Görüşmeyi platform dışına taşıma ifadeleri

## Gizlilik
Analiz kural tabanlı olarak uygulama içinde çalışır. Mesaj içeriği bu özellik için harici yapay zekâ servisine gönderilmez.

## Sınırlar
Bu sistem hukuki veya finansal güvence vermez. Uyarı bulunmaması mesajın güvenli olduğunu kanıtlamaz. Kullanıcılar ödeme öncesi karşı tarafı ve işlem ayrıntılarını ayrıca doğrulamalıdır.
