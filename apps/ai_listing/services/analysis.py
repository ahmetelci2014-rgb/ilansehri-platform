from __future__ import annotations

from hashlib import sha256
from time import monotonic

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.listings.models import Category

from ..models import AIAnalysis, AISettings
from .exceptions import AIListingError, FeatureDisabledError, UsageLimitError
from .image_processor import prepare_images
from .providers import get_provider
from .schemas import validate_analysis_payload


ANALYSIS_INSTRUCTIONS = """
Fotoğraflardaki ürünü yalnız görünür kanıtlara dayanarak analiz et. Görülmeyen marka, model,
teknik özellik veya ürün durumunu kesinmiş gibi yazma. Görülebilen çizik, kırık ve deformasyonları
gizleme. Telefon numarası, kimlik, plaka veya adres ihtimali varsa pii_warnings alanına ekle.
Yasaklı, tehlikeli, sahte veya mevzuata aykırı içerikte safety_status değerini blocked yap.
Fiyat üretme. Sonucu yalnız sözleşmedeki JSON alanlarıyla döndür.
""".strip()


def _today_queryset():
    today = timezone.localdate()
    return AIAnalysis.objects.filter(created_at__date=today)


def _increment_stats(config: AISettings, *, status: str, duration_ms: int):
    updates = {"total_duration_ms": F("total_duration_ms") + max(duration_ms, 0)}
    if status == AIAnalysis.Status.SUCCEEDED:
        updates["successful_analyses"] = F("successful_analyses") + 1
    elif status == AIAnalysis.Status.BLOCKED:
        updates["blocked_analyses"] = F("blocked_analyses") + 1
    else:
        updates["failed_analyses"] = F("failed_analyses") + 1
    AISettings.objects.filter(pk=config.pk).update(**updates)


def analyze_listing_images(*, user, files, idempotency_key: str, form_snapshot=None) -> AIAnalysis:
    config = AISettings.load()
    if not config.is_enabled:
        raise FeatureDisabledError("Yapay Zekâ ile İlan Hazırla özelliği şu anda kapalı.")
    if config.provider == AISettings.Provider.MOCK and not user.is_staff:
        raise FeatureDisabledError("Test sağlayıcısı yalnızca personel hesaplarıyla kullanılabilir.")
    idempotency_key = (idempotency_key or "").strip()[:80]
    if len(idempotency_key) < 12:
        raise AIListingError("Geçerli bir istek anahtarı oluşturulamadı.")

    existing = AIAnalysis.objects.filter(user=user, idempotency_key=idempotency_key).first()
    if existing:
        return existing

    prepared = prepare_images(
        files,
        max_images=config.max_images,
        max_image_size_mb=config.max_image_size_mb,
    )
    request_hash = sha256("|".join(image.fingerprint for image in prepared).encode("ascii")).hexdigest()

    # Ayar satırı kısa süre kilitlenerek eşzamanlı isteklerin limitleri aşması engellenir.
    with transaction.atomic():
        config = AISettings.objects.select_for_update().get(pk=config.pk)
        if not config.is_enabled:
            raise FeatureDisabledError("Yapay Zekâ ile İlan Hazırla özelliği şu anda kapalı.")
        existing = AIAnalysis.objects.filter(user=user, idempotency_key=idempotency_key).first()
        if existing:
            return existing
        today = _today_queryset()
        if today.filter(user=user).count() >= config.user_daily_limit:
            raise UsageLimitError("Bugünkü yapay zekâ ilan hazırlama limitine ulaştın.")
        if today.count() >= config.site_daily_limit:
            raise UsageLimitError("Site geneli günlük yapay zekâ kullanım limiti doldu.")
        duplicate = today.filter(
            user=user,
            request_hash=request_hash,
            status__in=[
                AIAnalysis.Status.PROCESSING,
                AIAnalysis.Status.SUCCEEDED,
                AIAnalysis.Status.BLOCKED,
            ],
        ).first()
        if duplicate:
            return duplicate
        analysis = AIAnalysis.objects.create(
            user=user,
            status=AIAnalysis.Status.PROCESSING,
            provider=config.provider,
            model_name=config.model_name,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            image_count=len(prepared),
            image_fingerprints=[image.fingerprint for image in prepared],
            form_snapshot=form_snapshot or {},
            started_at=timezone.now(),
        )

    started = monotonic()
    try:
        provider = get_provider(config.provider)
        categories = list(Category.objects.filter(is_active=True).values("id", "slug", "name", "parent_id"))
        response = provider.analyze(
            images=prepared,
            context={
                "model_name": config.model_name,
                "instructions": ANALYSIS_INSTRUCTIONS,
                "allowed_categories": categories,
            },
            timeout_seconds=config.timeout_seconds,
        )
        validated = validate_analysis_payload(
            response.payload,
            allowed_category_slugs={row["slug"] for row in categories},
        )
        category_by_slug = {row["slug"]: row for row in categories}
        chosen_slug = validated.get("subcategory_slug") or validated.get("category_slug")
        chosen = category_by_slug.get(chosen_slug)
        validated["category_id"] = chosen["id"] if chosen else None
        parent = category_by_slug.get(validated.get("category_slug"))
        if chosen and chosen.get("parent_id"):
            parent = next((row for row in categories if row["id"] == chosen["parent_id"]), parent)
        kind_by_parent_slug = {
            "urun-esya": "product",
            "arac": "vehicle",
            "emlak": "real_estate",
            "hizmet": "service",
            "is": "job",
            "ihtiyaclar": "need",
        }
        validated["kind"] = kind_by_parent_slug.get((parent or {}).get("slug", ""), "")
        duration_ms = round((monotonic() - started) * 1000)
        safety_status = validated["safety_status"]
        status = AIAnalysis.Status.BLOCKED if safety_status == "blocked" else AIAnalysis.Status.SUCCEEDED
        with transaction.atomic():
            analysis.status = status
            analysis.safety_status = safety_status
            analysis.validated_output = validated if status != AIAnalysis.Status.BLOCKED else {}
            analysis.confidence_score = validated["confidence_score"]
            analysis.safety_warnings = [*validated["safety_warnings"], *validated["pii_warnings"]]
            analysis.missing_questions = validated["missing_questions"]
            analysis.duration_ms = duration_ms
            analysis.provider_request_id = response.request_id[:160]
            analysis.completed_at = timezone.now()
            analysis.save()
            _increment_stats(config, status=status, duration_ms=duration_ms)
        return analysis
    except Exception as exc:
        duration_ms = round((monotonic() - started) * 1000)
        code = getattr(exc, "code", "unexpected_error")
        analysis.status = AIAnalysis.Status.FAILED
        analysis.error_code = str(code)[:80]
        analysis.error_message = str(exc)[:1000]
        analysis.duration_ms = duration_ms
        analysis.completed_at = timezone.now()
        analysis.save()
        _increment_stats(config, status=AIAnalysis.Status.FAILED, duration_ms=duration_ms)
        if isinstance(exc, AIListingError):
            raise
        raise AIListingError("Fotoğraflar analiz edilirken beklenmeyen bir hata oluştu.") from exc


_DIRECT_FIELD_MAP = {
    "title": "title",
    "description": "description",
    "condition": "condition",
    "brand": "brand",
    "model": "model_name",
    "kind": "kind",
    "category_id": "category_id",
}


def record_analysis_application(*, analysis_id: str, user, listing):
    """AI önerileri ile kullanıcının kaydettiği son değerleri karşılaştırır."""
    from ..models import AIFieldChange

    try:
        analysis = AIAnalysis.objects.filter(
            public_id=analysis_id,
            user=user,
            status=AIAnalysis.Status.SUCCEEDED,
            listing__isnull=True,
        ).first()
    except (ValidationError, ValueError, TypeError):
        return None
    if analysis is None:
        return None
    output = analysis.validated_output or {}
    changes = []
    for output_name, listing_name in _DIRECT_FIELD_MAP.items():
        suggested = output.get(output_name)
        if suggested in (None, "", []):
            continue
        final_value = getattr(listing, listing_name, None)
        if hasattr(final_value, "pk"):
            final_value = final_value.pk
        suggested_text = str(suggested).strip()
        final_text = str(final_value or "").strip()
        if not final_text:
            change_type = AIFieldChange.ChangeType.CLEARED
        elif suggested_text.casefold() == final_text.casefold():
            change_type = AIFieldChange.ChangeType.ACCEPTED
        else:
            change_type = AIFieldChange.ChangeType.EDITED
        changes.append(
            AIFieldChange(
                analysis=analysis,
                listing=listing,
                field_name=listing_name,
                suggested_value=suggested,
                final_value=final_value,
                change_type=change_type,
            )
        )
    with transaction.atomic():
        if changes:
            AIFieldChange.objects.bulk_create(changes)
        analysis.listing = listing
        analysis.applied_at = timezone.now()
        analysis.save(update_fields=["listing", "applied_at", "updated_at"])
    return analysis
