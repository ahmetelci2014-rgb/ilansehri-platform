from decimal import Decimal, InvalidOperation

from .locations import CITY_CHOICES

SESSION_KEY = "market_location"
LOCATION_KEYS = ("city", "district", "neighborhood", "lat", "lng", "radius")
VALID_RADII = {"5", "10", "25", "50", "100"}
VALID_CITIES = {value for value, _label in CITY_CHOICES}


def _decimal(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _preference_from_params(params):
    lat = _decimal(params.get("lat", ""))
    lng = _decimal(params.get("lng", ""))

    if (
        lat is not None
        and lng is not None
        and -90 <= lat <= 90
        and -180 <= lng <= 180
    ):
        radius = str(params.get("radius", "25")).strip()
        if radius not in VALID_RADII:
            radius = "25"

        preference = {
            "mode": "nearby",
            "lat": str(lat),
            "lng": str(lng),
            "radius": radius,
        }

        city = str(params.get("city", "")).strip()
        district = str(params.get("district", "")).strip()[:80]
        neighborhood = str(params.get("neighborhood", "")).strip()[:120]

        if city in VALID_CITIES:
            preference["city"] = city
        if district:
            preference["district"] = district
        if neighborhood:
            preference["neighborhood"] = neighborhood

        return preference

    city = str(params.get("city", "")).strip()
    if city in VALID_CITIES:
        preference = {
            "mode": "city",
            "city": city,
        }

        district = str(params.get("district", "")).strip()[:80]
        neighborhood = str(params.get("neighborhood", "")).strip()[:120]

        if district:
            preference["district"] = district
        if neighborhood:
            preference["neighborhood"] = neighborhood

        return preference

    return {}


def _profile_preference(request):
    if not request.user.is_authenticated:
        return {}

    city = str(request.user.city or "").strip()
    if city not in VALID_CITIES:
        return {}

    preference = {
        "mode": "city",
        "city": city,
    }

    district = str(request.user.district or "").strip()[:80]
    if district:
        preference["district"] = district

    return preference


def effective_listing_params(request):
    cached = getattr(request, "_market_location_params", None)
    if cached is not None:
        return cached

    params = request.GET.copy()
    reset = bool(params.pop("location_reset", None))

    if reset:
        request.session[SESSION_KEY] = {"mode": "all"}
    else:
        incoming = _preference_from_params(params)

        if incoming:
            request.session[SESSION_KEY] = incoming

        saved = request.session.get(SESSION_KEY)

        if not isinstance(saved, dict):
            saved = {}

        if not saved:
            saved = _profile_preference(request)
            if saved:
                request.session[SESSION_KEY] = saved

        if saved.get("mode") != "all":
            for key in LOCATION_KEYS:
                value = saved.get(key)
                if value and not params.get(key):
                    params[key] = value

            if (
                saved.get("mode") == "nearby"
                and saved.get("lat")
                and saved.get("lng")
                and not params.get("sort")
            ):
                params["sort"] = "nearby"

    request._market_location_params = params
    return params


def header_location_context(request):
    params = effective_listing_params(request)

    preference = _preference_from_params(params)

    if not preference:
        saved = request.session.get(SESSION_KEY, {})
        if isinstance(saved, dict):
            preference = saved

    city = str(preference.get("city", ""))
    radius = str(preference.get("radius", "25"))

    if radius not in VALID_RADII:
        radius = "25"

    is_nearby = (
        preference.get("mode") == "nearby"
        and bool(preference.get("lat"))
        and bool(preference.get("lng"))
    )

    if preference.get("mode") == "all":
        label = "Tüm Türkiye"
    elif city:
        label = city
    elif is_nearby:
        label = f"Yakınımda · {radius} km"
    else:
        label = "Tüm Türkiye"

    return {
        "header_location_label": label,
        "header_location_city": city,
        "header_location_radius": radius,
        "header_location_is_nearby": is_nearby,
    }
