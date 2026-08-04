# v1.12.2.1 Gemini Revizyonu — Dosya Dosya Değişiklik Raporu

## Yapay zekâ uygulaması

- `apps/ai_listing/models.py` — Google Gemini sağlayıcısı ve `gemini-3.6-flash` varsayılan modeli eklendi; OpenAI yedek olarak korundu.
- `apps/ai_listing/forms.py` — yönetim paneli açıklamaları Gemini birincil sağlayıcısına göre güncellendi.
- `apps/ai_listing/templatetags/ai_listing_tags.py` — Gemini anahtar/model durumu ve kullanıcıya gösterilen kurulum mesajları eklendi.
- `apps/ai_listing/services/providers.py` — Gemini Interactions API, base64 görsel girişi, JSON Schema çıktısı, bağlantı testi, hata ve güvenlik engeli işleme eklendi.
- `apps/ai_listing/services/schemas.py` — sağlayıcıdan bağımsız şema açıklaması güncellendi.
- `apps/ai_listing/management/commands/activate_gemini_ai.py` — Gemini sağlayıcısını ve modeli tek komutla seçen güvenli yönetim komutu eklendi.
- `apps/ai_listing/tests.py` — Gemini istek gövdesi, görsel girişi, JSON şeması ve güvenlik engeli için testler eklendi.

## Ortam ve operasyon

- `.env.example` — `GEMINI_API_KEY`, `GEMINI_API_BASE`, `GEMINI_API_REVISION` ve `GEMINI_MODEL` örnekleri eklendi; gerçek anahtar içermez.
- `scripts/start_codespace.sh` — sürüm bildirimi v1.12.2.1 olarak güncellendi.
- `apps/core/views.py` — PWA önbelleği `ilansehri-v11221` olarak yenilendi.
- `templates/base.html` — sürüm etiketi ve AI statik dosya önbellek kırıcıları güncellendi.
- `VERSION` — `v1.12.2.1`.
- `README.md` — Gemini kurulumu ve mevcut özellik özeti güncellendi.
- `CHANGELOG.md` — Gemini revizyonu eklendi.
- `docs/AI_LISTING_V1122.md` — Gemini kurulum, güvenlik ve gizlilik rehberi güncellendi.

## Dokunulmayan ana akışlar

- Mevcut ilan oluşturma ve düzenleme view'ları yeniden yazılmadı.
- Üyelik, taslak, mesajlaşma, teklif, destek ve moderasyon modelleri değiştirilmedi.
- Mavi–turuncu tasarım ve fotoğrafla başlayan kullanıcı akışı korundu.
- Fiyat tahmini eklenmedi.
