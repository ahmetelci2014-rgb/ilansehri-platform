from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re
import unicodedata

from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .models import Listing, ListingMatch, Notification


_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "acil", "ariyorum", "araniyor", "aranmaktadir", "ilan", "istiyorum", "lazim",
    "satilik", "kiralik", "takas", "temiz", "uygun", "fiyat", "fiyatli", "sahibinden",
    "urun", "esya", "hizmet", "is", "ve", "ile", "icin", "bir", "bu", "olan",
    "model", "marka", "adet", "cok", "az", "kullanilmis", "sifir", "gibi", "tercihen",
}
_TRANSLATION = str.maketrans(
    {
        "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
        "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
    }
)


@dataclass(frozen=True)
class MatchScore:
    score: int
    reasons: list[str]


def normalize_text(value: object) -> str:
    text = str(value or "").translate(_TRANSLATION).lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


def _normalized_words(value: object) -> str:
    return " ".join(_WORD_RE.findall(normalize_text(value)))


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_text = f" {_normalized_words(text)} "
    normalized_phrase = _normalized_words(phrase)
    return bool(normalized_phrase) and f" {normalized_phrase} " in normalized_text


def _tokens(*values: object) -> set[str]:
    text = " ".join(normalize_text(value) for value in values if value)
    return {
        token
        for token in _WORD_RE.findall(text)
        if len(token) >= 3 and token not in _STOP_WORDS and not token.isdigit()
    }


def _category_root(listing: Listing):
    category = listing.category
    return category.parent or category


def _category_text(listing: Listing) -> str:
    category = listing.category
    parts = [category.name]
    if category.parent_id:
        parts.append(category.parent.name)
    return " ".join(parts)


def is_request_listing(listing: Listing) -> bool:
    return listing.kind == Listing.Kind.NEED or listing.action in {
        Listing.Action.WANTED,
        Listing.Action.SERVICE_REQUEST,
        Listing.Action.JOB_REQUEST,
    }


def is_offer_listing(listing: Listing) -> bool:
    return listing.action in {
        Listing.Action.SELL,
        Listing.Action.RENT,
        Listing.Action.SWAP,
        Listing.Action.SERVICE_OFFER,
        Listing.Action.JOB_OFFER,
    }


def requested_kind(listing: Listing) -> str | None:
    if listing.kind != Listing.Kind.NEED:
        return listing.kind
    combined = f"{_category_text(listing)} {listing.title} {listing.description}"
    keyword_map = (
        (Listing.Kind.VEHICLE, ("arac", "otomobil", "motosiklet", "yedek parca", "kamyon", "traktor")),
        (Listing.Kind.REAL_ESTATE, ("emlak", "konut", "daire", "ev", "isyeri", "arsa", "dukkan")),
        (Listing.Kind.SERVICE, ("hizmet", "usta", "tamir", "temizlik", "nakliye", "ders", "bakim")),
        (Listing.Kind.JOB, ("is ariyorum", "calisan", "personel", "eleman", "meslek")),
        (Listing.Kind.PRODUCT, ("urun", "esya", "telefon", "elektronik", "mobilya", "giyim", "makine")),
    )
    for kind, keywords in keyword_map:
        if any(_contains_phrase(combined, keyword) for keyword in keywords):
            return kind
    return None


def compatible_offer_actions(wanted: Listing) -> set[str]:
    target_kind = requested_kind(wanted)
    text = normalize_text(f"{_category_text(wanted)} {wanted.title} {wanted.description}")
    if wanted.action == Listing.Action.SERVICE_REQUEST or target_kind == Listing.Kind.SERVICE:
        return {Listing.Action.SERVICE_OFFER}
    if wanted.action == Listing.Action.JOB_REQUEST or target_kind == Listing.Kind.JOB:
        return {Listing.Action.JOB_OFFER}
    if "takas" in text:
        return {Listing.Action.SWAP}
    if "kiralik" in text or "kirala" in text:
        return {Listing.Action.RENT}
    return {Listing.Action.SELL, Listing.Action.RENT, Listing.Action.SWAP}


def _listing_tokens(listing: Listing) -> set[str]:
    tags = " ".join(str(item) for item in (listing.search_tags or []))
    features = " ".join(str(item) for item in (listing.technical_features or []))
    return _tokens(
        listing.title,
        listing.description,
        listing.brand,
        listing.model_name,
        listing.condition,
        tags,
        features,
    )


def score_listing_pair(wanted: Listing, offered: Listing) -> MatchScore | None:
    if wanted.pk == offered.pk or wanted.owner_id == offered.owner_id:
        return None
    if not is_request_listing(wanted) or not is_offer_listing(offered):
        return None
    if wanted.status != Listing.Status.PUBLISHED or offered.status != Listing.Status.PUBLISHED:
        return None
    if offered.action not in compatible_offer_actions(wanted):
        return None

    target_kind = requested_kind(wanted)
    if target_kind and offered.kind != target_kind:
        return None

    score = 10
    reasons: list[str] = []
    if target_kind and offered.kind == target_kind:
        score += 18
        reasons.append("İlan türü uyumlu")

    wanted_root = _category_root(wanted)
    offered_root = _category_root(offered)
    exact_category = wanted.category_id == offered.category_id
    same_root = wanted_root.pk == offered_root.pk
    if exact_category:
        score += 30
        reasons.append("Aynı kategori")
    elif same_root:
        score += 18
        reasons.append("Yakın kategori")

    wanted_brand = normalize_text(wanted.brand)
    offered_brand = normalize_text(offered.brand)
    exact_brand = bool(wanted_brand and offered_brand and wanted_brand == offered_brand)
    similar_brand = bool(
        wanted_brand
        and offered_brand
        and (wanted_brand in offered_brand or offered_brand in wanted_brand)
    )
    if wanted_brand and offered_brand:
        if exact_brand:
            score += 14
            reasons.append("Marka eşleşiyor")
        elif similar_brand:
            score += 7
            reasons.append("Marka benzer")
        else:
            return None

    wanted_model = normalize_text(wanted.model_name)
    offered_model = normalize_text(offered.model_name)
    exact_model = bool(wanted_model and offered_model and wanted_model == offered_model)
    similar_model = bool(
        wanted_model
        and offered_model
        and (wanted_model in offered_model or offered_model in wanted_model)
    )
    if wanted_model and offered_model:
        if exact_model:
            score += 14
            reasons.append("Model eşleşiyor")
        elif similar_model:
            score += 8
            reasons.append("Model benzer")
        else:
            return None

    common_tokens = sorted(_listing_tokens(wanted) & _listing_tokens(offered))
    if common_tokens:
        token_score = min(28, len(common_tokens) * 7)
        score += token_score
        reasons.append("Ortak özellikler: " + ", ".join(common_tokens[:3]))
    elif not exact_brand and not exact_model:
        # Açık marka/model beklentisi varken yalnız kategori ve konum eşleşmesi
        # yeterli değildir. Geniş, marka/model belirtmeyen aramalar ise aynı
        # kategoride sonuç alabilir.
        if wanted_brand or wanted_model or not exact_category:
            return None

    if normalize_text(wanted.city) == normalize_text(offered.city):
        score += 15
        reasons.append("Aynı şehir")
        if wanted.district and normalize_text(wanted.district) == normalize_text(offered.district):
            score += 7
            reasons.append("Aynı ilçe")

    if wanted.price is not None and offered.price is not None and wanted.price > 0:
        budget = Decimal(wanted.price)
        offer_price = Decimal(offered.price)
        if offer_price <= budget:
            score += 8
            reasons.append("Bütçeye uygun")
        elif offer_price <= budget * Decimal("1.15"):
            score += 3
            reasons.append("Bütçeye yakın")
        elif offer_price > budget * Decimal("1.35"):
            score -= 10

    if wanted.delivery_type and wanted.delivery_type == offered.delivery_type:
        score += 3
        reasons.append("Teslim şekli uyumlu")

    score = max(0, min(100, score))
    if score < 50:
        return None
    return MatchScore(score=score, reasons=reasons[:6])


def _active_published_queryset():
    now = timezone.now()
    return (
        Listing.objects.filter(status=Listing.Status.PUBLISHED, owner__is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .select_related("owner", "category", "category__parent")
    )


def _notify_wanted_owner(match: ListingMatch) -> None:
    if match.notified_wanted_at:
        return
    from .services import create_notification

    create_notification(
        user=match.wanted_listing.owner,
        actor=match.offered_listing.owner,
        listing=match.offered_listing,
        notification_type=Notification.Type.MATCH,
        title="Aradığın ilana uygun yeni bir seçenek bulundu",
        body=f"%{match.score} uyum · {match.offered_listing.title}",
        link=f"{reverse('listings:matches')}?tab=wanted&highlight={match.pk}",
    )
    match.notified_wanted_at = timezone.now()
    match.save(update_fields=["notified_wanted_at", "updated_at"])


def _notify_offered_owner(match: ListingMatch) -> None:
    if match.notified_offered_at:
        return
    from .services import create_notification

    create_notification(
        user=match.offered_listing.owner,
        actor=match.wanted_listing.owner,
        listing=match.offered_listing,
        notification_type=Notification.Type.MATCH,
        title="İlanına uygun bir arayan bulundu",
        body=f"%{match.score} uyum · {match.wanted_listing.title}",
        link=f"{reverse('listings:matches')}?tab=offered&highlight={match.pk}",
    )
    match.notified_offered_at = timezone.now()
    match.save(update_fields=["notified_offered_at", "updated_at"])


def blocked_owner_ids(user_id: int) -> set[int]:
    from apps.accounts.models import UserBlock

    blocked = set(
        UserBlock.objects.filter(blocker_id=user_id).values_list("blocked_id", flat=True)
    )
    blocked.update(
        UserBlock.objects.filter(blocked_id=user_id).values_list("blocker_id", flat=True)
    )
    return blocked


@transaction.atomic
def sync_listing_matches(listing: Listing, *, notify: bool = True, max_matches: int = 30) -> dict:
    listing = Listing.objects.select_related("owner", "category", "category__parent").get(pk=listing.pk)
    if listing.status != Listing.Status.PUBLISHED:
        deleted, _ = ListingMatch.objects.filter(
            Q(wanted_listing=listing) | Q(offered_listing=listing)
        ).delete()
        return {"created": 0, "updated": 0, "deleted": deleted, "matches": []}

    pairs: list[tuple[Listing, Listing, MatchScore]] = []
    excluded_owner_ids = blocked_owner_ids(listing.owner_id)
    if is_request_listing(listing):
        candidates = (
            _active_published_queryset()
            .exclude(owner_id=listing.owner_id)
            .exclude(owner_id__in=excluded_owner_ids)
            .filter(action__in=compatible_offer_actions(listing))
        )
        target_kind = requested_kind(listing)
        if target_kind:
            candidates = candidates.filter(kind=target_kind)
        for offered in candidates.iterator(chunk_size=200):
            result = score_listing_pair(listing, offered)
            if result:
                pairs.append((listing, offered, result))
    elif is_offer_listing(listing):
        candidates = (
            _active_published_queryset()
            .exclude(owner_id=listing.owner_id)
            .exclude(owner_id__in=excluded_owner_ids)
            .filter(
                Q(kind=Listing.Kind.NEED)
                | Q(action__in=[Listing.Action.WANTED, Listing.Action.SERVICE_REQUEST, Listing.Action.JOB_REQUEST])
            )
        )
        for wanted in candidates.iterator(chunk_size=200):
            result = score_listing_pair(wanted, listing)
            if result:
                pairs.append((wanted, listing, result))
    else:
        deleted, _ = ListingMatch.objects.filter(
            Q(wanted_listing=listing) | Q(offered_listing=listing)
        ).delete()
        return {"created": 0, "updated": 0, "deleted": deleted, "matches": []}

    pairs.sort(key=lambda item: item[2].score, reverse=True)
    created_count = 0
    updated_count = 0
    records: list[ListingMatch] = []
    newly_created: list[ListingMatch] = []
    for wanted, offered, result in pairs[:max_matches]:
        match, created = ListingMatch.objects.update_or_create(
            wanted_listing=wanted,
            offered_listing=offered,
            defaults={"score": result.score, "reasons": result.reasons},
        )
        records.append(match)
        if created:
            created_count += 1
            newly_created.append(match)
        else:
            updated_count += 1

    if is_request_listing(listing):
        valid_counterpart_ids = [offered.pk for _, offered, _ in pairs]
        stale_matches = ListingMatch.objects.filter(wanted_listing=listing)
        if valid_counterpart_ids:
            stale_matches = stale_matches.exclude(offered_listing_id__in=valid_counterpart_ids)
    else:
        valid_counterpart_ids = [wanted.pk for wanted, _, _ in pairs]
        stale_matches = ListingMatch.objects.filter(offered_listing=listing)
        if valid_counterpart_ids:
            stale_matches = stale_matches.exclude(wanted_listing_id__in=valid_counterpart_ids)
    deleted_count, _ = stale_matches.delete()

    if notify and newly_created:
        for match in newly_created[:5]:
            _notify_wanted_owner(match)
        if is_request_listing(listing):
            for match in newly_created[:3]:
                _notify_offered_owner(match)
        else:
            for match in newly_created[:5]:
                _notify_offered_owner(match)

    return {
        "created": created_count,
        "updated": updated_count,
        "deleted": deleted_count,
        "matches": records,
    }


def refresh_user_matches(user, *, notify: bool = False) -> dict:
    listings = _active_published_queryset().filter(owner=user)
    created = 0
    updated = 0
    deleted = 0
    scanned = 0
    for listing in listings.iterator(chunk_size=100):
        result = sync_listing_matches(listing, notify=notify)
        created += result["created"]
        updated += result["updated"]
        deleted += result.get("deleted", 0)
        scanned += 1
    return {"scanned": scanned, "created": created, "updated": updated, "deleted": deleted}
