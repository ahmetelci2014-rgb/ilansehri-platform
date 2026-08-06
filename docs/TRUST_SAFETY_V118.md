# İlan Şehri v1.18.0 — Güvenilir Satıcı ve Dolandırıcılık Koruması

## Amaç

v1.18.0, kullanıcıya doğrulanabilir güven işaretleri gösterirken şüpheli durumları yetkili ekibin inceleyebileceği açıklanabilir kayıtlara dönüştürür. Sistem tek bir sinyale dayanarak kullanıcıyı suçlu ilan etmez, hesabı otomatik kapatmaz veya ilanı otomatik silmez.

## Satıcı güven profili

Güven profili şu sinyallerden oluşur:

- telefon ve e-posta doğrulaması,
- kimlik veya profesyonel doğrulama seviyesi,
- hesap yaşı,
- tamamlanan ve uyuşmazlığa düşen işlem kayıtları,
- kullanıcı değerlendirmesi,
- satıcının örnek konuşmalardaki ortalama ilk yanıt süresi.

Kamuya açık profilde yalnız güven göstergeleri ve rozetler görünür. Açık şikâyet veya iç risk kaydı sayısı yalnız personele gösterilir.

## Risk olayları

Aşağıdaki olaylar açıklanabilir personel inceleme kaydı oluşturabilir:

- yüksek veya kritik riskli mesaj,
- ilan açıklamasında platform dışı ödeme, telefon veya bağlantı,
- olağan dışı düşük fiyat,
- başka hesaplarda kullanılan ilan fotoğrafı,
- ilan şikâyeti,
- kullanıcı şikâyeti.

Her olayın türü, önem seviyesi, gerekçeleri, ilgili ilan/mesaj ve inceleme durumu saklanır. Personel olayı incelemeye alabilir, çözebilir veya işlem gerektirmiyor olarak kapatabilir.

## Fotoğraf tekrar kontrolü

İlan fotoğrafları yüklenirken dosyanın SHA-256 parmak izi hesaplanır. Kontrol yalnız yerel veritabanındaki parmak izlerini karşılaştırır. Görsel içeriği üçüncü taraf bir servise gönderilmez. Aynı kullanıcının kendi ilanlarında yeniden kullandığı fotoğraf farklı hesap tekrarı olarak sayılmaz.

## Kullanıcı şikâyeti

- Kullanıcı kendi hesabını şikâyet edemez.
- Aynı hedef için açık ikinci şikâyet oluşturamaz.
- Saatlik gönderim sınırı uygulanır.
- Şikâyet, ilgili satıcıya ait bir ilana bağlanabilir.
- Şikâyet ayrıntıları kamuya açık profile yansımaz.
- Kullanıcı kendi gönderdiği şikâyetleri hesap veri ihracında görebilir.

## Geriye uyumluluk

Başlangıç scriptleri `ensure_v118_schema` ile eksik güvenlik tablolarını ve görsel parmak izi sütununu kontrol eder. `backfill_image_fingerprints` mevcut görsellerin boş parmak izlerini tamamlar. Eski kullanıcı, ilan ve mesaj verileri değiştirilmez.

## Operasyon ilkesi

Risk göstergeleri karar destek aracıdır. Hesap kapatma, ilan kaldırma ve kullanıcı yaptırımı yalnız yetkili personelin doğrulamasından sonra uygulanmalıdır.
