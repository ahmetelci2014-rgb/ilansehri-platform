"""Kayıtlı arama filtreleri, yakınlık hesabı ve bildirim eşleştirme yardımcıları.

Bu modül liste ekranı ile zamanlanmış bildirim işinin aynı filtre sözleşmesini
kullanmasını sağlar. Böylece kullanıcı ekranda gördüğü aramayla aynı sonuçlar
için bildirim alır.
"""
from __future__ import annotations

import re

from decimal import Decimal, InvalidOperation
from math import asin, cos, radians, sin, sqrt

from django.db.models import F, OuterRef, Q, Subquery
from django.utils import timezone

from apps.accounts.models import UserFollow

from .catalog import descendant_category_ids
from .models import Listing, ListingPriceHistory


ALLOWED_SAVED_SEARCH_PARAMS = {
    "q",
    "city",
    "district",
    "neighborhood",
    "kind",
    "action",
    "category",
    "brand",
    "model",
    "condition",
    "color",
    "delivery_type",
    "fuel_type",
    "transmission",
    "fee_type",
    "job_type",
    "room_count",
    "heating_type",
    "floor_location",
    "service_area",
    "experience_level",
    "managed",
    "verified",
    "price_drop",
    "following",
    "min_price",
    "max_price",
    "min_year",
    "max_year",
    "max_mileage",
    "min_area",
    "max_area",
    "max_building_age",
    "lat",
    "lng",
    "radius",
}

TRUTHY_FILTERS = {"managed", "verified", "price_drop", "following"}
MAX_TEXT_LENGTHS = {
    "q": 80,
    "city": 80,
    "district": 80,
    "neighborhood": 120,
    "brand": 100,
    "model": 100,
    "condition": 50,
    "color": 60,
    "room_count": 30,
    "heating_type": 80,
    "floor_location": 60,
    "service_area": 160,
    "experience_level": 80,
}
ALLOWED_RADIUS_KM = (5, 10, 25, 50, 100)



_LISTING_NUMBER_PATTERNS = (
    re.compile(r"^(?:#\s*)?(\d+)$"),
    re.compile(r"^ilan(?:\s+no)?\s*[:#-]?\s*(\d+)$"),
)


def parse_listing_number_query(value):
    text = " ".join(str(value or "").strip().split())
    text = text.casefold().replace("i̇", "i")
    for pattern in _LISTING_NUMBER_PATTERNS:
        match = pattern.fullmatch(text)
        if not match:
            continue
        digits = match.group(1)
        if len(digits) > 18:
            return None
        number = int(digits)
        return number if number > 0 else None
    return None


def _get(params, key: str, default=""):
    value = params.get(key, default) if hasattr(params, "get") else default
    if isinstance(value, (list, tuple)):
        value = value[-1] if value else default
    return value


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_decimal(value):
    try:
        candidate = Decimal(str(value))
        return candidate if candidate.is_finite() else None
    except (TypeError, ValueError, InvalidOperation):
        return None


def normalize_saved_search_params(params) -> dict[str, str]:
    """Yalnız desteklenen, kısa ve güvenli filtre değerlerini sakla."""
    cleaned: dict[str, str] = {}
    for key in ALLOWED_SAVED_SEARCH_PARAMS:
        raw = _get(params, key, "")
        value = str(raw).strip()
        if not value:
            continue
        if key in TRUTHY_FILTERS:
            if value == "1":
                cleaned[key] = "1"
            continue
        if key in MAX_TEXT_LENGTHS:
            cleaned[key] = value[: MAX_TEXT_LENGTHS[key]]
            continue
        if key in {"kind", "action", "delivery_type", "fuel_type", "transmission", "fee_type", "job_type"}:
            cleaned[key] = value[:32]
            continue
        if key in {"category", "min_year", "max_year", "max_mileage", "min_area", "max_area", "max_building_age"}:
            parsed = _safe_int(value)
            if parsed is not None and parsed >= 0:
                cleaned[key] = str(parsed)
            continue
        if key in {"min_price", "max_price"}:
            parsed = _safe_decimal(value)
            if parsed is not None and parsed >= 0:
                cleaned[key] = format(parsed, "f")
            continue
        if key in {"lat", "lng"}:
            parsed = _safe_decimal(value)
            limit = Decimal("90") if key == "lat" else Decimal("180")
            if parsed is not None and -limit <= parsed <= limit:
                cleaned[key] = format(parsed.quantize(Decimal("0.001")), "f")
            continue
        if key == "radius":
            parsed = _safe_int(value)
            if parsed in ALLOWED_RADIUS_KM:
                cleaned[key] = str(parsed)
    return cleaned


def annotate_price_history(qs):
    latest = ListingPriceHistory.objects.filter(listing_id=OuterRef("pk")).order_by("-created_at")
    return qs.annotate(
        latest_price_old=Subquery(latest.values("old_price")[:1]),
        latest_price_new=Subquery(latest.values("new_price")[:1]),
        latest_price_changed_at=Subquery(latest.values("created_at")[:1]),
    )


def parse_nearby_params(params):
    lat = _safe_decimal(_get(params, "lat", ""))
    lng = _safe_decimal(_get(params, "lng", ""))
    radius = _safe_int(_get(params, "radius", "25"))
    if lat is None or lng is None or not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return None
    if radius not in ALLOWED_RADIUS_KM:
        radius = 25
    return float(lat), float(lng), radius


def apply_listing_filters(qs, params, *, user=None):
    """Liste ekranı ve kayıtlı aramalar için ortak filtre sözleşmesi."""
    params = normalize_saved_search_params(params)
    q = params.get("q", "")
    if q:
        listing_number = parse_listing_number_query(q)
        if listing_number is not None and qs.filter(pk=listing_number).exists():
            qs = qs.filter(pk=listing_number)
        else:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(category__name__icontains=q)
                | Q(brand__icontains=q)
                | Q(model_name__icontains=q)
                | Q(color__icontains=q)
            )

    exact_filters = {
        "city": "city__iexact",
        "kind": "kind",
        "action": "action",
        "room_count": "room_count",
        "delivery_type": "delivery_type",
        "fuel_type": "fuel_type",
        "transmission": "transmission",
        "fee_type": "fee_type",
        "job_type": "job_type",
    }
    partial_filters = {
        "district": "district__iexact",
        "neighborhood": "neighborhood__iexact",
        "brand": "brand__icontains",
        "model": "model_name__icontains",
        "condition": "condition__icontains",
        "color": "color__icontains",
        "heating_type": "heating_type__icontains",
        "floor_location": "floor_location__icontains",
        "service_area": "service_area__icontains",
        "experience_level": "experience_level__icontains",
    }
    category_id = _safe_int(params.get("category"))
    if category_id:
        qs = qs.filter(category_id__in=descendant_category_ids(category_id))

    for key, lookup in exact_filters.items():
        value = params.get(key)
        if value:
            qs = qs.filter(**{lookup: value})
    for key, lookup in partial_filters.items():
        value = params.get(key)
        if value:
            qs = qs.filter(**{lookup: value})

    numeric_filters = {
        "min_price": ("price__gte", _safe_decimal),
        "max_price": ("price__lte", _safe_decimal),
        "min_year": ("model_year__gte", _safe_int),
        "max_year": ("model_year__lte", _safe_int),
        "max_mileage": ("mileage__lte", _safe_int),
        "min_area": ("area_m2__gte", _safe_int),
        "max_area": ("area_m2__lte", _safe_int),
        "max_building_age": ("building_age__lte", _safe_int),
    }
    for key, (lookup, parser) in numeric_filters.items():
        if key in params:
            parsed = parser(params[key])
            if parsed is not None:
                qs = qs.filter(**{lookup: parsed})

    if params.get("managed") == "1":
        qs = qs.filter(management_mode=Listing.ManagementMode.FULL)
    if params.get("verified") == "1":
        qs = qs.filter(owner__is_phone_verified=True)
    if params.get("price_drop") == "1":
        qs = annotate_price_history(qs).filter(latest_price_old__gt=F("latest_price_new"))
    if params.get("following") == "1":
        if user is None or not getattr(user, "is_authenticated", False):
            return qs.none()
        followed_ids = UserFollow.objects.filter(follower=user).values_list("seller_id", flat=True)
        qs = qs.filter(owner_id__in=followed_ids)

    nearby = parse_nearby_params(params)
    if nearby:
        lat, lng, radius = nearby
        lat_delta = radius / 111.0
        lng_factor = max(cos(radians(lat)), 0.15)
        lng_delta = radius / (111.0 * lng_factor)
        qs = qs.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=lat - lat_delta,
            latitude__lte=lat + lat_delta,
            longitude__gte=lng - lng_delta,
            longitude__lte=lng + lng_delta,
        )
    return qs




def saved_search_result_params(params) -> dict[str, str]:
    """Kayıtlı aramayı açarken güvenli filtreleri kullanıcı dostu sıralamayla döndür."""
    result = normalize_saved_search_params(params)
    if parse_nearby_params(result):
        result["sort"] = "nearby"
    return result

def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 6371.0088 * 2 * asin(min(1.0, sqrt(a)))


def attach_nearby_distances(items, params):
    """Yakınlık filtresini kesin mesafeyle tamamlar ve mesafeyi nesneye ekler."""
    nearby = parse_nearby_params(params)
    if not nearby:
        return list(items)
    lat, lng, radius = nearby
    matched = []
    for item in items:
        if item.latitude is None or item.longitude is None:
            continue
        distance = haversine_distance_km(lat, lng, float(item.latitude), float(item.longitude))
        if distance <= radius:
            item.distance_km = round(distance, 1)
            matched.append(item)
    return matched


def listing_matches_saved_search(saved_search, listing: Listing) -> bool:
    if listing.owner_id == saved_search.user_id or listing.status != Listing.Status.PUBLISHED:
        return False
    if listing.expires_at and listing.expires_at <= timezone.now():
        return False
    qs = Listing.objects.filter(pk=listing.pk)
    qs = apply_listing_filters(qs, saved_search.query_params or {}, user=saved_search.user)
    items = attach_nearby_distances(qs, saved_search.query_params or {})
    return bool(items)
