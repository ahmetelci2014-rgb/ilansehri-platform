# İlan Şehri Mobil Görsel Denetim

v1.14.0 sürümünde de kullanılan mobil denetim altyapısı, mobil sorunları kullanıcıdan tek tek istemek yerine gerçek tarayıcıda düzenli olarak ölçmek için iki katmanlı kontrol kullanır.

## 1. Mobil sözleşme kontrolü

Ana `Django Kontrol` workflow'u şu komutu çalıştırır:

```bash
python scripts/check_mobile_contract.py
```

Bu kontrol:

- sürüm ve PWA cache numarasını,
- mobil CSS/JavaScript dosyalarının ortak şablonda yüklendiğini,
- hesap, mesaj, teklif, destek, operasyon ve yönetim sayfalarının CSS kapsamını,
- kullanıcı sayfalarının ortak `base.html` kabuğunu kullandığını,
- riskli sabit inline genişliklerin bulunmadığını

doğrular. Bu adım bağımlılıksızdır ve ana testleri kırabilecek paket eksiklerini hızlı yakalar.

## 2. Playwright mobil ekran denetimi

`Mobil Görsel Denetim` workflow'u Chromium'u açarak demo verisiyle şu ekranları tarar:

- 360 × 800
- 390 × 844
- 430 × 932

Ziyaretçi, alıcı, satıcı, görev ortağı ve yönetici akışları ayrı oturumlarda incelenir. Her sayfada:

- tam sayfa ekran görüntüsü,
- HTTP durumu,
- yatay taşma miktarı,
- taşan öğe listesi,
- küçük dokunma hedefi sayısı,
- JavaScript konsol ve sayfa hataları

kaydedilir.

Workflow sonucu engelleyici değildir. Ekran görüntüleri ile `mobile-audit.json`, `mobile-audit.md` ve sunucu günlüğü GitHub Actions artifact'i olarak 14 gün tutulur.

## Yerel kullanım

Django sunucusu ve demo verisi hazırken:

```bash
pip install playwright
python -m playwright install chromium
python scripts/mobile_audit.py \
  --base-url http://127.0.0.1:8000 \
  --output mobile-audit-artifacts
```

Kritik hata veya yatay taşmada başarısız çıkış kodu için:

```bash
python scripts/mobile_audit.py --strict
```

Sayfayı elle incelerken URL'ye `?mobile_audit=1` eklendiğinde taşan öğeler kırmızı kesik çizgiyle işaretlenir ve rapor tarayıcı konsoluna yazılır.


## v1.14 kapsamı

Akıllı Eşleşmeler sayfası alıcı ve satıcı rol rotalarına eklenmiştir. Mobil denetim 360, 390 ve 430 piksel genişliklerde eşleşme kartlarını, sekmeleri ve işlem düğmelerini de görüntüler.
