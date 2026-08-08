"""Kategori ağacı ile ilan türü arasındaki ortak sözleşme.

Veritabanında kategori türü için ayrı bir alan tutulmuyor. Kök kategori slug'ı
tek kaynak kabul edilir; böylece eski ilanlar ve mevcut kategori kayıtları şema
değişikliği olmadan profesyonel kategori/filtre deneyimine katılır.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.db.models import QuerySet

from .models import Category, Listing


ROOT_KIND_MAP = {
    "urun-esya": Listing.Kind.PRODUCT,
    "arac": Listing.Kind.VEHICLE,
    "emlak": Listing.Kind.REAL_ESTATE,
    "hizmet": Listing.Kind.SERVICE,
    "is": Listing.Kind.JOB,
    "ihtiyaclar": Listing.Kind.NEED,
}

KIND_ROOT_SLUG_MAP = {value: key for key, value in ROOT_KIND_MAP.items()}

KIND_ICONS = {
    Listing.Kind.PRODUCT: "▣",
    Listing.Kind.VEHICLE: "🚘",
    Listing.Kind.REAL_ESTATE: "⌂",
    Listing.Kind.SERVICE: "🛠",
    Listing.Kind.JOB: "💼",
    Listing.Kind.NEED: "◎",
}


# v1.25.2 — alt kategoriye göre profesyonel ilan ayrıntı sözleşmesi.
#
# Ön yüz ve backend aynı alan sözleşmesini kullanır. Böylece örneğin
# "Araç > Yedek Parça" ilanı kilometre/yakıt istemez; "Satılık Arsa"
# ilanı da oda sayısı istemez.
CATEGORY_DETAIL_PROFILE_FIELDS = {
    "generic": (
        "search_tags_text",
        "technical_features_text",
    ),

    "product_tech": (
        "condition",
        "delivery_type",
        "brand",
        "model_name",
        "color",
        "search_tags_text",
        "technical_features_text",
    ),
    "product_home": (
        "condition",
        "delivery_type",
        "brand",
        "model_name",
        "color",
        "search_tags_text",
        "technical_features_text",
    ),
    "product_style": (
        "condition",
        "delivery_type",
        "brand",
        "color",
        "search_tags_text",
        "technical_features_text",
    ),
    "product_general": (
        "condition",
        "delivery_type",
        "brand",
        "color",
        "search_tags_text",
        "technical_features_text",
    ),
    "product_food": (
        "delivery_type",
        "brand",
        "search_tags_text",
        "technical_features_text",
    ),

    "vehicle_full": (
        "condition",
        "delivery_type",
        "brand",
        "model_name",
        "color",
        "model_year",
        "mileage",
        "fuel_type",
        "transmission",
        "search_tags_text",
        "technical_features_text",
    ),
    "vehicle_parts": (
        "condition",
        "delivery_type",
        "brand",
        "model_name",
        "color",
        "search_tags_text",
        "technical_features_text",
    ),

    "estate_residential": (
        "room_count",
        "area_m2",
        "building_age",
        "floor_location",
        "heating_type",
        "search_tags_text",
        "technical_features_text",
    ),
    "estate_land": (
        "area_m2",
        "search_tags_text",
        "technical_features_text",
    ),
    "estate_commercial": (
        "area_m2",
        "building_age",
        "floor_location",
        "heating_type",
        "search_tags_text",
        "technical_features_text",
    ),

    "service": (
        "delivery_type",
        "service_area",
        "fee_type",
        "search_tags_text",
        "technical_features_text",
    ),
    "job": (
        "job_type",
        "experience_level",
        "search_tags_text",
        "technical_features_text",
    ),

    "need_product": (
        "brand",
        "model_name",
        "color",
        "search_tags_text",
        "technical_features_text",
    ),
    "need_vehicle": (
        "brand",
        "model_name",
        "model_year",
        "search_tags_text",
        "technical_features_text",
    ),
    "need_estate": (
        "room_count",
        "area_m2",
        "search_tags_text",
        "technical_features_text",
    ),
    "need_service": (
        "service_area",
        "fee_type",
        "search_tags_text",
        "technical_features_text",
    ),
    "need_job": (
        "job_type",
        "experience_level",
        "search_tags_text",
        "technical_features_text",
    ),
    "need_generic": (
        "search_tags_text",
        "technical_features_text",
    ),
}


CATEGORY_DETAIL_PROFILE_REQUIRED = {
    "product_tech": ("condition",),
    "product_home": ("condition",),
    "product_style": ("condition",),
    "product_general": ("condition",),

    "vehicle_full": (
        "brand",
        "model_name",
        "model_year",
    ),
    "vehicle_parts": ("condition",),

    "estate_residential": (
        "room_count",
        "area_m2",
    ),
    "estate_land": ("area_m2",),
    "estate_commercial": ("area_m2",),

    "service": (
        "service_area",
        "fee_type",
    ),
    "job": ("job_type",),
}


DEFAULT_KIND_DETAIL_PROFILE = {
    Listing.Kind.PRODUCT: "product_general",
    Listing.Kind.VEHICLE: "vehicle_full",
    Listing.Kind.REAL_ESTATE: "estate_residential",
    Listing.Kind.SERVICE: "service",
    Listing.Kind.JOB: "job",
    Listing.Kind.NEED: "need_generic",
}


def _category_slug_contains(slug: str, *parts: str) -> bool:
    return any(part in slug for part in parts)


def category_detail_profile(category: Category | None, kind: str = "") -> str:
    """Alt kategoriye göre form ayrıntı profilini döndür.

    Türkçe kategori adlarında slug dönüşümündeki ı/i gibi farklılıklara
    güvenilmez. Profesyonel katalog adı birincil kaynak kabul edilir.
    """
    market_kind = category_market_kind(category) or kind
    name = " ".join(
        str(getattr(category, "name", "") or "")
        .replace("İ", "i")
        .split()
    ).casefold()

    if market_kind == Listing.Kind.PRODUCT:
        if name in {
            "cep telefonu & aksesuar",
            "bilgisayar & tablet",
            "tv & ses sistemleri",
            "fotoğraf & kamera",
            "oyun & konsol",
        }:
            return "product_tech"

        if name in {
            "beyaz eşya",
            "küçük ev aletleri",
            "ev & mobilya",
            "bahçe & yapı market",
            "makine & ekipman",
        }:
            return "product_home"

        if name in {
            "giyim & aksesuar",
            "ayakkabı & çanta",
            "anne, bebek & çocuk",
            "spor & outdoor",
        }:
            return "product_style"

        if name == "yeme & içme":
            return "product_food"

        return "product_general"

    if market_kind == Listing.Kind.VEHICLE:
        if name in {
            "yedek parça",
            "jant & lastik",
            "araç aksesuarı",
        }:
            return "vehicle_parts"

        return "vehicle_full"

    if market_kind == Listing.Kind.REAL_ESTATE:
        if name in {
            "satılık arsa",
            "tarla & bahçe",
        }:
            return "estate_land"

        if name in {
            "satılık daire",
            "kiralık daire",
            "müstakil ev & villa",
            "rezidans",
            "günlük kiralık",
        }:
            return "estate_residential"

        if name in {
            "kiralık işyeri",
            "satılık işyeri",
            "ofis",
            "dükkan & mağaza",
            "depo & antrepo",
            "devren işletme",
            "turistik tesis",
            "diğer emlak",
        }:
            return "estate_commercial"

        return "estate_residential"

    if market_kind == Listing.Kind.SERVICE:
        return "service"

    if market_kind == Listing.Kind.JOB:
        return "job"

    if market_kind == Listing.Kind.NEED:
        if name == "ürün arıyorum":
            return "need_product"

        if name == "araç arıyorum":
            return "need_vehicle"

        if name in {
            "kiralık ev arıyorum",
            "satılık ev arıyorum",
        }:
            return "need_estate"

        if name in {
            "hizmet arıyorum",
            "usta arıyorum",
        }:
            return "need_service"

        if name in {
            "çalışan arıyorum",
            "iş arıyorum",
        }:
            return "need_job"

        return "need_generic"

    return DEFAULT_KIND_DETAIL_PROFILE.get(
        market_kind,
        "generic",
    )


def category_detail_fields(
    category: Category | None,
    kind: str = "",
) -> tuple[str, ...]:
    profile = category_detail_profile(category, kind)
    return CATEGORY_DETAIL_PROFILE_FIELDS.get(
        profile,
        CATEGORY_DETAIL_PROFILE_FIELDS["generic"],
    )


def category_required_fields(
    category: Category | None,
    kind: str = "",
    action: str = "",
) -> tuple[str, ...]:
    profile = category_detail_profile(category, kind)
    required = CATEGORY_DETAIL_PROFILE_REQUIRED.get(profile, ())

    # Arıyorum ilanlarında kullanıcı kesin teknik bilgi bilmiyor olabilir.
    if action == Listing.Action.WANTED:
        return ()

    # Hizmet arayan kişide ücret tipi zorunlu değildir;
    # hizmetin yapılacağı bölge yeterlidir.
    if action == Listing.Action.SERVICE_REQUEST:
        if profile in {"service", "need_service"}:
            return tuple(
                field for field in required
                if field == "service_area"
            )
        return ()

    return required


def category_root(category: Category | None) -> Category | None:
    """Kategori ağacının kökünü güvenli biçimde döndür."""
    current = category
    visited: set[int] = set()
    while current and current.parent_id and current.pk not in visited:
        if current.pk:
            visited.add(current.pk)
        current = current.parent
    return current


def category_market_kind(category: Category | None) -> str:
    root = category_root(category)
    return ROOT_KIND_MAP.get(getattr(root, "slug", ""), "")


def category_path(category: Category | None) -> str:
    if not category:
        return ""
    names: list[str] = []
    current = category
    visited: set[int] = set()
    while current and current.pk not in visited:
        if current.pk:
            visited.add(current.pk)
        names.append(current.name)
        current = current.parent
    return " / ".join(reversed(names))


def category_matches_kind(category: Category | None, kind: str) -> bool:
    market_kind = category_market_kind(category)
    return not market_kind or not kind or market_kind == kind


def descendant_category_ids(category_id: int) -> list[int]:
    """Seçilen kategori ve bütün alt kategorilerinin kimliklerini döndür."""
    discovered = {category_id}
    frontier = {category_id}
    while frontier:
        children = set(
            Category.objects.filter(parent_id__in=frontier, is_active=True).values_list("pk", flat=True)
        )
        children -= discovered
        if not children:
            break
        discovered.update(children)
        frontier = children
    return sorted(discovered)


def category_options(queryset: QuerySet[Category] | Iterable[Category]) -> list[dict]:
    """Şablon ve JS için kategori ağacını sıralı bir seçenek listesine dönüştür."""
    categories = list(queryset)
    children_by_parent: dict[int | None, list[Category]] = {}
    for category in categories:
        children_by_parent.setdefault(category.parent_id, []).append(category)
    for children in children_by_parent.values():
        children.sort(key=lambda item: (item.sort_order, item.name.casefold()))

    result: list[dict] = []

    def walk(item: Category, depth: int) -> None:
        children = children_by_parent.get(item.pk, [])
        market_kind = category_market_kind(item)
        result.append(
            {
                "id": item.pk,
                "name": item.name,
                "path": category_path(item),
                "depth": depth,
                "kind": market_kind,
                "is_leaf": not children,
                "icon": item.icon or KIND_ICONS.get(market_kind, "▦"),
            }
        )
        for child in children:
            walk(child, depth + 1)

    for root in children_by_parent.get(None, []):
        walk(root, 0)
    return result
