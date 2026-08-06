from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from .models import AIAnalysis, AISettings
from .services.analysis import analyze_listing_images
from .services.exceptions import AIListingError
from .services.providers import provider_is_configured


def _analysis_payload(analysis: AIAnalysis):
    try:
        minimum_confidence = AISettings.load().min_confidence_score
    except Exception:
        minimum_confidence = 60
    return {
        "analysis_id": str(analysis.public_id),
        "status": analysis.status,
        "safety_status": analysis.safety_status,
        "confidence_score": analysis.confidence_score,
        "minimum_confidence": minimum_confidence,
        "result": analysis.validated_output if analysis.status == AIAnalysis.Status.SUCCEEDED else {},
        "missing_questions": analysis.missing_questions,
        "safety_warnings": analysis.safety_warnings,
        "error": analysis.error_message if analysis.status == AIAnalysis.Status.FAILED else "",
    }


@login_required
@require_GET
def availability(request):
    config = AISettings.load()
    today_count = AIAnalysis.objects.filter(user=request.user, created_at__date=timezone.localdate()).count()
    provider_ready = provider_is_configured(config.provider)
    mock_allowed = config.provider != AISettings.Provider.MOCK or request.user.is_staff
    return JsonResponse(
        {
            "enabled": config.is_enabled,
            "configured": provider_ready,
            "can_analyze": bool(config.is_enabled and provider_ready and mock_allowed),
            "max_images": config.max_images,
            "max_image_size_mb": config.max_image_size_mb,
            "provider": config.provider,
            "model_name": config.model_name,
            "user_daily_limit": config.user_daily_limit,
            "used_today": today_count,
        }
    )


@login_required
@require_POST
def analyze(request):
    try:
        snapshot_raw = request.POST.get("form_snapshot", "")
        snapshot = json.loads(snapshot_raw) if snapshot_raw else {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        allowed_snapshot_fields = {"kind", "action", "category", "condition", "brand", "model_name"}
        snapshot = {
            key: str(value)[:180]
            for key, value in snapshot.items()
            if key in allowed_snapshot_fields and value not in (None, "")
        }
        analysis = analyze_listing_images(
            user=request.user,
            files=request.FILES.getlist("images"),
            idempotency_key=request.POST.get("request_id", ""),
            form_snapshot=snapshot,
        )
        status_code = 200 if analysis.status != AIAnalysis.Status.PROCESSING else 202
        return JsonResponse(_analysis_payload(analysis), status=status_code)
    except (json.JSONDecodeError, AIListingError) as exc:
        return JsonResponse(
            {"status": "failed", "error_code": getattr(exc, "code", "invalid_request"), "error": str(exc)},
            status=400,
        )


@login_required
@require_GET
def analysis_detail(request, public_id):
    analysis = AIAnalysis.objects.filter(public_id=public_id, user=request.user).first()
    if analysis is None:
        return JsonResponse({"error": "Analiz bulunamadı."}, status=404)
    return JsonResponse(_analysis_payload(analysis))
