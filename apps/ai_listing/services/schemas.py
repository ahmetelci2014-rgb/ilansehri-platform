from __future__ import annotations

from typing import Any

from .exceptions import SchemaValidationError


_ALLOWED_KEYS = {
    "schema_version",
    "title",
    "description",
    "category",
    "category_slug",
    "subcategory",
    "subcategory_slug",
    "condition",
    "brand",
    "model",
    "color",
    "tags",
    "detected_features",
    "possible_defects",
    "missing_questions",
    "field_confidence",
    "confidence_score",
    "safety_status",
    "safety_warnings",
    "pii_warnings",
}
_ALLOWED_SAFETY = {"safe", "review_required", "blocked"}


def _text(value: Any, *, field: str, limit: int) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise SchemaValidationError(f"{field} metin olmalıdır.")
    return " ".join(value.strip().split())[:limit]


def _text_list(value: Any, *, field: str, item_limit: int, count_limit: int) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise SchemaValidationError(f"{field} liste olmalıdır.")
    result: list[str] = []
    for item in value[:count_limit]:
        cleaned = _text(item, field=field, limit=item_limit)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _questions(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise SchemaValidationError("missing_questions liste olmalıdır.")
    result = []
    for item in value[:12]:
        if isinstance(item, str):
            question = _text(item, field="missing_questions", limit=220)
            if question:
                result.append({"field": "", "question": question, "type": "text", "options": [], "required": False})
            continue
        if not isinstance(item, dict):
            raise SchemaValidationError("Her eksik bilgi sorusu metin veya nesne olmalıdır.")
        question = _text(item.get("question"), field="missing_questions.question", limit=220)
        if not question:
            continue
        question_type = item.get("type", "text")
        if question_type not in {"text", "choice", "boolean", "number"}:
            question_type = "text"
        result.append(
            {
                "field": _text(item.get("field"), field="missing_questions.field", limit=80),
                "question": question,
                "type": question_type,
                "options": _text_list(item.get("options", []), field="missing_questions.options", item_limit=80, count_limit=12),
                "required": bool(item.get("required", False)),
            }
        )
    return result


def validate_analysis_payload(payload: Any, *, allowed_category_slugs: set[str]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SchemaValidationError("Yapay zekâ çıktısı JSON nesnesi olmalıdır.")
    unknown = set(payload) - _ALLOWED_KEYS
    if unknown:
        raise SchemaValidationError(f"Beklenmeyen JSON alanları: {', '.join(sorted(unknown))}")
    if "price" in payload:
        raise SchemaValidationError("İlk sürümde fiyat önerisi kabul edilmez.")

    confidence = payload.get("confidence_score", 0)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise SchemaValidationError("confidence_score sayı olmalıdır.")
    confidence = max(0, min(100, round(confidence)))

    safety_status = payload.get("safety_status", "review_required")
    if safety_status not in _ALLOWED_SAFETY:
        raise SchemaValidationError("Geçersiz safety_status değeri.")

    category_slug = _text(
        payload.get("category_slug") or payload.get("category"),
        field="category_slug",
        limit=140,
    ).lower()
    subcategory_slug = _text(
        payload.get("subcategory_slug") or payload.get("subcategory"),
        field="subcategory_slug",
        limit=140,
    ).lower()
    if category_slug and category_slug not in allowed_category_slugs:
        category_slug = ""
    if subcategory_slug and subcategory_slug not in allowed_category_slugs:
        subcategory_slug = ""

    field_confidence = payload.get("field_confidence", {}) or {}
    if not isinstance(field_confidence, dict):
        raise SchemaValidationError("field_confidence nesne olmalıdır.")
    cleaned_confidence: dict[str, int] = {}
    for key, value in list(field_confidence.items())[:30]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        cleaned_confidence[_text(key, field="field_confidence", limit=80)] = max(0, min(100, round(value)))

    result = {
        "schema_version": "1.0",
        "title": _text(payload.get("title"), field="title", limit=180),
        "description": _text(payload.get("description"), field="description", limit=5000),
        "category_slug": category_slug,
        "subcategory_slug": subcategory_slug,
        "condition": _text(payload.get("condition"), field="condition", limit=50),
        "brand": _text(payload.get("brand"), field="brand", limit=100),
        "model": _text(payload.get("model"), field="model", limit=100),
        "color": _text(payload.get("color"), field="color", limit=60),
        "tags": _text_list(payload.get("tags", []), field="tags", item_limit=40, count_limit=20),
        "detected_features": _text_list(payload.get("detected_features", []), field="detected_features", item_limit=160, count_limit=30),
        "possible_defects": _text_list(payload.get("possible_defects", []), field="possible_defects", item_limit=180, count_limit=20),
        "missing_questions": _questions(payload.get("missing_questions", [])),
        "field_confidence": cleaned_confidence,
        "confidence_score": confidence,
        "safety_status": safety_status,
        "safety_warnings": _text_list(payload.get("safety_warnings", []), field="safety_warnings", item_limit=240, count_limit=20),
        "pii_warnings": _text_list(payload.get("pii_warnings", []), field="pii_warnings", item_limit=240, count_limit=20),
    }

    if result["possible_defects"]:
        result["safety_status"] = "review_required" if result["safety_status"] == "safe" else result["safety_status"]
    if result["pii_warnings"]:
        result["safety_status"] = "review_required" if result["safety_status"] == "safe" else result["safety_status"]
    return result
