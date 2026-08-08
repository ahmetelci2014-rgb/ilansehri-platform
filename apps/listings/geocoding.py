"""İlan Şehri ters adres çözümleme servisi.

Tarayıcı üçüncü taraf servise doğrudan bağlanmaz. Koordinat Django'ya gelir;
Django yapılandırılabilir sağlayıcıya tek istek gönderir ve yalnız
il / ilçe / mahalle seviyesindeki sonucu kullanıcıya döndürür.

Varsayılan geliştirme sağlayıcısı Nominatim uyumludur. Canlı ortamda
REVERSE_GEOCODING_URL ile sağlayıcı değiştirilebilir.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

from .locations import (
    canonicalize_city,
    canonicalize_district,
    canonicalize_neighborhood,
)


class ReverseGeocodingError(RuntimeError):
    pass


class ReverseGeocodingBusy(ReverseGeocodingError):
    pass


def _admin(payload):
    value = payload.get("admin") or {}
    return value if isinstance(value, dict) else {}


def _first(values):
    for value in values:
        value = " ".join(str(value or "").split()).strip()
        if value:
            return value
    return ""


def parse_nominatim_geocodejson(payload: dict) -> dict:
    features = payload.get("features") or []

    # Bazı GeocodeJSON üreticileri tek feature nesnesi döndürebilir.
    if isinstance(features, dict):
        features = [features]

    if not features:
        return {}

    feature = features[0] or {}
    properties = feature.get("properties") or {}
    geocoding = properties.get("geocoding") or {}
    admin = _admin(geocoding)

    city = ""
    for candidate in (
        geocoding.get("state"),
        admin.get("level4"),
        geocoding.get("city"),
        geocoding.get("county"),
    ):
        city = canonicalize_city(candidate)
        if city:
            break

    if not city:
        return {}

    city_key = city.replace("İ", "i").replace("I", "ı").casefold()

    district = ""
    for candidate in (
        geocoding.get("district"),
        admin.get("level6"),
        admin.get("level7"),
        geocoding.get("county"),
        geocoding.get("city"),
    ):
        candidate = _first((candidate,))
        if not candidate:
            continue

        candidate_city = canonicalize_city(candidate)
        if candidate_city:
            continue

        normalized = canonicalize_district(city, candidate)
        if (
            normalized
            and normalized.replace("İ", "i").replace("I", "ı").casefold()
            != city_key
        ):
            district = normalized
            break

    neighborhood = ""
    for candidate in (
        geocoding.get("locality"),
        admin.get("level10"),
        admin.get("level9"),
        admin.get("level8"),
    ):
        candidate = _first((candidate,))
        if not candidate:
            continue

        normalized = canonicalize_neighborhood(
            city,
            district,
            candidate,
        )
        if not normalized:
            continue

        key = (
            normalized
            .replace("İ", "i")
            .replace("I", "ı")
            .casefold()
        )
        district_key = (
            district
            .replace("İ", "i")
            .replace("I", "ı")
            .casefold()
        )

        if key not in {city_key, district_key}:
            neighborhood = normalized
            break

    attribution = (
        (payload.get("geocoding") or {}).get("attribution")
        or "© OpenStreetMap contributors"
    )

    return {
        "city": city,
        "district": district,
        "neighborhood": neighborhood,
        "attribution": attribution,
    }


def reverse_geocode(latitude: float, longitude: float) -> dict:
    cache_key = (
        "ilansehri:reverse-geocode:"
        f"{float(latitude):.4f}:{float(longitude):.4f}"
    )

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if not settings.REVERSE_GEOCODING_ENABLED:
        raise ReverseGeocodingError(
            "Adres çözümleme servisi etkin değil."
        )

    # Varsayılan public sağlayıcı için istekleri seyrekleştir.
    # Bu kilit Codespaces/tek-process geliştirme ortamında koruma sağlar.
    if not cache.add(
        "ilansehri:reverse-geocode:provider-lock",
        "1",
        timeout=2,
    ):
        raise ReverseGeocodingBusy(
            "Adres servisi kısa süreli yoğun. Birkaç saniye sonra tekrar dene."
        )

    query = urlencode(
        {
            "format": "geocodejson",
            "lat": f"{float(latitude):.5f}",
            "lon": f"{float(longitude):.5f}",
            "zoom": "14",
            "addressdetails": "1",
            "layer": "address",
            "accept-language": "tr",
        }
    )

    endpoint = settings.REVERSE_GEOCODING_URL.rstrip("?")
    separator = "&" if "?" in endpoint else "?"

    request = Request(
        f"{endpoint}{separator}{query}",
        headers={
            "User-Agent": settings.REVERSE_GEOCODING_USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "tr",
        },
    )

    try:
        with urlopen(
            request,
            timeout=settings.REVERSE_GEOCODING_TIMEOUT,
        ) as response:
            if response.status != 200:
                raise ReverseGeocodingError(
                    f"Adres servisi HTTP {response.status} döndürdü."
                )

            payload = json.loads(
                response.read().decode("utf-8")
            )

    except HTTPError as exc:
        raise ReverseGeocodingError(
            f"Adres servisi HTTP {exc.code} döndürdü."
        ) from exc
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise ReverseGeocodingError(
            "Adres servisine şu anda ulaşılamıyor."
        ) from exc

    result = parse_nominatim_geocodejson(payload)

    if not result.get("city"):
        raise ReverseGeocodingError(
            "Bu koordinat için Türkiye içinde şehir bulunamadı."
        )

    # Tam açık adres veya yol bilgisi cache'e alınmaz.
    cache.set(
        cache_key,
        result,
        timeout=24 * 60 * 60,
    )

    return result
