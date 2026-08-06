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
