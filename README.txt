# İlan Şehri v0.3.1 düzeltmesi

Bu paket yalnızca `config/settings.py` dosyasını değiştirir.

Düzeltme:
- Django test çalıştırılırken üretim tipi statik dosya manifesti devre dışı bırakılır.
- `css/app.css` için oluşan `Missing staticfiles manifest entry` hatası giderilir.
- Canlı ortamda WhiteNoise manifest sistemi kullanılmaya devam eder.
