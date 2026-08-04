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
    "technical_attributes",
    "possible_defects",
    "missing_questions",
    "field_confidence",
    "confidence_score",
    "safety_status",
    "safety_warnings",
    "pii_warnings",
}
_ALLOWED_SAFETY = {"safe", "review_required", "blocked"}
_ALLOWED_TECHNICAL_KEYS = {
    "model_year",
    "mileage",
    "fuel_type",
    "transmission",
    "room_count",
    "area_m2",
    "building_age",
    "floor_location",
    "heating_type",
    "service_area",
    "fee_type",
    "job_type",
    "experience_level",
}
_CONFIDENCE_FIELDS = {
    "title",
    "description",
    "category",
    "condition",
    "brand",
    "model",
    "color",
    *_ALLOWED_TECHNICAL_KEYS,
}


def provider_json_schema() -> dict[str, Any]:
    """Gemini, OpenAI ve benzeri sağlayıcılar için katı çıktı sözleşmesi."""
    technical_properties = {
        key: {"type": "string"}
        for key in sorted(_ALLOWED_TECHNICAL_KEYS)
    }
    confidence_properties = {
        key: {"type": "integer"}
        for key in sorted(_CONFIDENCE_FIELDS)
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "string", "enum": ["1.0"]},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "category_slug": {"type": "string"},
            "subcategory_slug": {"type": "string"},
            "condition": {"type": "string"},
            "brand": {"type": "string"},
            "model": {"type": "string"},
            "color": {"type": "string"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            },
            "detected_features": {
                "type": "array",
                "items": {"type": "string"},
            },
            "technical_attributes": {
                "type": "object",
                "additionalProperties": False,
                "properties": technical_properties,
                "required": sorted(_ALLOWED_TECHNICAL_KEYS),
            },
            "possible_defects": {
                "type": "array",
                "items": {"type": "string"},
            },
            "missing_questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "field": {"type": "string"},
                        "question": {"type": "string"},
                        "type": {"type": "string", "enum": ["text", "choice", "boolean", "number"]},
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "required": {"type": "boolean"},
                    },
                    "required": ["field", "question", "type", "options", "required"],
                },
            },
            "field_confidence": {
                "type": "object",
                "additionalProperties": False,
                "properties": confidence_properties,
                "required": sorted(_CONFIDENCE_FIELDS),
            },
            "confidence_score": {"type": "integer"},
            "safety_status": {"type": "string", "enum": sorted(_ALLOWED_SAFETY)},
            "safety_warnings": {
                "type": "array",
                "items": {"type": "string"},
            },
            "pii_warnings": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "schema_version",
            "title",
            "description",
            "category_slug",
            "subcategory_slug",
            "condition",
            "brand",
            "model",
            "color",
            "tags",
            "detected_features",
            "technical_attributes",
            "possible_defects",
            "missing_questions",
            "field_confidence",
            "confidence_score",
            "safety_status",
            "safety_warnings",
            "pii_warnings",
        ],
    }


def _text(value: Any, *, field: str, limit: int) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        value = str(value)
    return " ".join(value.strip().split())[:limit]


def _text_list(value: Any, *, field: str, item_limit: int, count_limit: int) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise SchemaValidationError(f"{field} liste olmalıdır.")
    result: list[str] = []
    seen: set[str] = set()
    for item in value[:count_limit]:
        cleaned = _text(item, field=field, limit=item_limit)
        folded = cleaned.casefold()
        if cleaned and folded not in seen:
            result.append(cleaned)
            seen.add(folded)
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


def _technical_attributes(value: Any) -> dict[str, str]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise SchemaValidationError("technical_attributes nesne olmalıdır.")
    result = {}
    for key in _ALLOWED_TECHNICAL_KEYS:
        cleaned = _text(value.get(key), field=f"technical_attributes.{key}", limit=160)
        if cleaned:
            result[key] = cleaned
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
    for key, value in list(field_confidence.items())[:40]:
        if key not in _CONFIDENCE_FIELDS:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        cleaned_confidence[key] = max(0, min(100, round(value)))

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
        "technical_attributes": _technical_attributes(payload.get("technical_attributes", {})),
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
