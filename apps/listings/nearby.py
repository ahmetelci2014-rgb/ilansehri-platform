from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import asin, cos, radians, sin, sqrt
from typing import Iterable


EARTH_RADIUS_KM = 6371.0088
ALLOWED_RADII_KM = (5, 10, 25, 50, 100, 200)
DEFAULT_RADIUS_KM = 25


@dataclass(frozen=True)
class NearbyOrigin:
    latitude: float
    longitude: float
    radius_km: int = DEFAULT_RADIUS_KM


def _to_float(value: object) -> float | None:
    try:
        candidate = float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return candidate


def parse_origin(latitude: object, longitude: object, radius: object = None) -> NearbyOrigin | None:
    lat = _to_float(latitude)
    lon = _to_float(longitude)
    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return None
    try:
        radius_km = int(radius or DEFAULT_RADIUS_KM)
    except (TypeError, ValueError):
        radius_km = DEFAULT_RADIUS_KM
    if radius_km not in ALLOWED_RADII_KM:
        radius_km = DEFAULT_RADIUS_KM
    return NearbyOrigin(latitude=lat, longitude=lon, radius_km=radius_km)


def haversine_km(lat1: object, lon1: object, lat2: object, lon2: object) -> float:
    values = [_to_float(value) for value in (lat1, lon1, lat2, lon2)]
    if any(value is None for value in values):
        raise ValueError("Geçerli enlem ve boylam değerleri gerekli.")
    first_lat, first_lon, second_lat, second_lon = values
    lat_delta = radians(second_lat - first_lat)
    lon_delta = radians(second_lon - first_lon)
    a = (
        sin(lat_delta / 2) ** 2
        + cos(radians(first_lat)) * cos(radians(second_lat)) * sin(lon_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def bounding_box(origin: NearbyOrigin) -> tuple[float, float, float, float]:
    latitude_delta = origin.radius_km / 111.0
    longitude_factor = max(abs(cos(radians(origin.latitude))), 0.05)
    longitude_delta = origin.radius_km / (111.0 * longitude_factor)
    return (
        origin.latitude - latitude_delta,
        origin.latitude + latitude_delta,
        origin.longitude - longitude_delta,
        origin.longitude + longitude_delta,
    )


def distance_label(distance_km: float | None) -> str:
    if distance_km is None:
        return "Aynı bölgede"
    if distance_km < 1:
        meters = max(50, round(distance_km * 1000 / 50) * 50)
        return f"Yaklaşık {meters} m"
    if distance_km < 10:
        return f"Yaklaşık {distance_km:.1f} km".replace(".", ",")
    return f"Yaklaşık {round(distance_km)} km"


def attach_distance(listing, origin: NearbyOrigin) -> float | None:
    if listing.latitude is None or listing.longitude is None:
        listing.distance_km = None
        listing.distance_label = "Aynı bölgede"
        listing.nearby_fallback = True
        return None
    distance = round(
        haversine_km(origin.latitude, origin.longitude, listing.latitude, listing.longitude),
        2,
    )
    listing.distance_km = distance
    listing.distance_label = distance_label(distance)
    listing.nearby_fallback = False
    return distance


def _timestamp(value) -> float:
    if value is None:
        return 0.0
    try:
        return value.timestamp()
    except (AttributeError, OSError, OverflowError, ValueError):
        return 0.0


def sort_nearby_listings(items: Iterable, sort: str = "distance") -> list:
    listings = list(items)

    def rank(item) -> int:
        return 1 if getattr(item, "nearby_fallback", False) else 0

    def distance(item) -> float:
        value = getattr(item, "distance_km", None)
        return float(value) if value is not None else float("inf")

    if sort == "price_asc":
        return sorted(
            listings,
            key=lambda item: (
                rank(item),
                item.price is None,
                float(item.price or 0),
                distance(item),
            ),
        )
    if sort == "price_desc":
        return sorted(
            listings,
            key=lambda item: (
                rank(item),
                item.price is None,
                -float(item.price or 0),
                distance(item),
            ),
        )
    if sort == "popular":
        return sorted(
            listings,
            key=lambda item: (
                rank(item),
                -int(item.view_count or 0),
                -int(item.favorite_count or 0),
                distance(item),
            ),
        )
    if sort == "oldest":
        return sorted(
            listings,
            key=lambda item: (rank(item), _timestamp(item.created_at), distance(item)),
        )
    if sort == "newest":
        return sorted(
            listings,
            key=lambda item: (rank(item), -_timestamp(item.published_at or item.created_at), distance(item)),
        )
    if sort == "price_drop":
        return sorted(
            listings,
            key=lambda item: (
                rank(item),
                -_timestamp(getattr(item, "latest_price_changed_at", None)),
                distance(item),
            ),
        )
    return sorted(
        listings,
        key=lambda item: (
            rank(item),
            distance(item),
            -int(bool(item.is_featured)),
            -_timestamp(item.published_at or item.created_at),
        ),
    )
