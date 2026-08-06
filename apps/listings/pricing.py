from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from django.db.models import Q, QuerySet
from django.utils import timezone

from .models import Listing


SUPPORTED_KINDS = {
    Listing.Kind.PRODUCT,
    Listing.Kind.VEHICLE,
    Listing.Kind.REAL_ESTATE,
}
SUPPORTED_ACTIONS = {
    Listing.Action.SELL,
    Listing.Action.RENT,
}


@dataclass(frozen=True)
class PriceGuide:
    available: bool
    sample_count: int = 0
    lower_price: Decimal | None = None
    median_price: Decimal | None = None
    upper_price: Decimal | None = None
    status: str = "unavailable"
    status_label: str = "Fiyat karşılaştırılamadı"
    confidence: str = "none"
    confidence_label: str = "Veri yok"
    message: str = ""
    criteria: tuple[str, ...] = ()
    removed_outliers: int = 0

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("lower_price", "median_price", "upper_price"):
            value = payload[key]
            payload[key] = str(value.quantize(Decimal("1"))) if value is not None else None
        payload["criteria"] = list(self.criteria)
        return payload


@dataclass(frozen=True)
class _CandidatePlan:
    filters: dict
    minimum: int
    label: str
    specificity: int


def _normalize(value: object) -> str:
    return " ".join(str(value or "").casefold().strip().split())


def _percentile(values: list[Decimal], fraction: Decimal) -> Decimal:
    if not values:
        raise ValueError("Boş fiyat listesinde yüzdelik hesaplanamaz.")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = Decimal(len(ordered) - 1) * fraction
    lower_index = int(position.to_integral_value(rounding=ROUND_FLOOR))
    upper_index = int(position.to_integral_value(rounding=ROUND_CEILING))
    if lower_index == upper_index:
        return ordered[lower_index]
    weight = position - Decimal(lower_index)
    return ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * weight


def _remove_outliers(values: list[Decimal]) -> tuple[list[Decimal], int]:
    ordered = sorted(value for value in values if value > 0)
    if len(ordered) < 6:
        return ordered, 0

    q1 = _percentile(ordered, Decimal("0.25"))
    q3 = _percentile(ordered, Decimal("0.75"))
    iqr = q3 - q1
    if iqr > 0:
        lower_fence = max(Decimal("0"), q1 - (iqr * Decimal("1.5")))
        upper_fence = q3 + (iqr * Decimal("1.5"))
    else:
        median = _percentile(ordered, Decimal("0.5"))
        lower_fence = median * Decimal("0.50")
        upper_fence = median * Decimal("2.00")

    filtered = [value for value in ordered if lower_fence <= value <= upper_fence]
    if len(filtered) < 4:
        return ordered, 0
    return filtered, len(ordered) - len(filtered)


def _market_step(value: Decimal) -> Decimal:
    if value < Decimal("1000"):
        return Decimal("10")
    if value < Decimal("10000"):
        return Decimal("100")
    if value < Decimal("100000"):
        return Decimal("500")
    if value < Decimal("1000000"):
        return Decimal("5000")
    if value < Decimal("10000000"):
        return Decimal("10000")
    return Decimal("50000")


def _round_market(value: Decimal, *, direction: str = "nearest") -> Decimal:
    step = _market_step(value)
    quotient = value / step
    rounding = {
        "down": ROUND_FLOOR,
        "up": ROUND_CEILING,
        "nearest": ROUND_HALF_UP,
    }[direction]
    return quotient.to_integral_value(rounding=rounding) * step


def _active_price_queryset(subject: Listing, *, exclude_pk: int | None = None) -> QuerySet:
    now = timezone.now()
    queryset = (
        Listing.objects.filter(
            status=Listing.Status.PUBLISHED,
            owner__is_active=True,
            kind=subject.kind,
            action=subject.action,
            price_on_request=False,
            price__isnull=False,
            price__gt=0,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .exclude(owner_id=subject.owner_id)
    )
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset


def _category_filters(subject: Listing) -> tuple[dict, dict]:
    exact = {"category_id": subject.category_id}
    category = subject.category
    root_id = category.parent_id or category.pk
    if category.parent_id:
        root = {"category__parent_id": root_id}
    else:
        root = Q(category_id=root_id) | Q(category__parent_id=root_id)
    return exact, {"_root_q": root}


def _product_plans(subject: Listing) -> list[_CandidatePlan]:
    exact, root = _category_filters(subject)
    brand = _normalize(subject.brand)
    model = _normalize(subject.model_name)
    city = _normalize(subject.city)
    plans: list[_CandidatePlan] = []

    def add(filters: dict, minimum: int, label: str, specificity: int) -> None:
        plans.append(_CandidatePlan(filters=filters, minimum=minimum, label=label, specificity=specificity))

    if brand and model:
        add({**exact, "brand__iexact": subject.brand, "model_name__icontains": subject.model_name, "city__iexact": subject.city}, 4, "Aynı kategori, marka, model ve şehir", 5)
        add({**exact, "brand__iexact": subject.brand, "model_name__icontains": subject.model_name}, 4, "Aynı kategori, marka ve model", 5)
    if brand:
        add({**exact, "brand__iexact": subject.brand, "city__iexact": subject.city}, 5, "Aynı kategori, marka ve şehir", 4)
        add({**exact, "brand__iexact": subject.brand}, 5, "Aynı kategori ve marka", 4)
    if city:
        add({**exact, "city__iexact": subject.city}, 5, "Aynı kategori ve şehir", 3)
    add(exact, 5, "Aynı kategori", 3)
    if city:
        add({**root, "city__iexact": subject.city}, 7, "Yakın kategori ve aynı şehir", 2)
    add(root, 8, "Yakın kategori", 1)
    return plans


def _vehicle_plans(subject: Listing) -> list[_CandidatePlan]:
    exact, root = _category_filters(subject)
    plans: list[_CandidatePlan] = []
    brand = _normalize(subject.brand)
    model = _normalize(subject.model_name)

    def add(filters: dict, minimum: int, label: str, specificity: int) -> None:
        plans.append(_CandidatePlan(filters=filters, minimum=minimum, label=label, specificity=specificity))

    year_filters = {}
    if subject.model_year:
        year_filters = {
            "model_year__gte": max(1900, subject.model_year - 2),
            "model_year__lte": subject.model_year + 2,
        }
    mileage_filters = {}
    if subject.mileage is not None and subject.mileage > 0:
        mileage_filters = {
            "mileage__gte": max(0, int(subject.mileage * 0.45)),
            "mileage__lte": int(subject.mileage * 1.65) + 5000,
        }

    if brand and model:
        add({**exact, "brand__iexact": subject.brand, "model_name__icontains": subject.model_name, **year_filters, **mileage_filters}, 4, "Aynı marka, model, yakın yıl ve kilometre", 5)
        add({**exact, "brand__iexact": subject.brand, "model_name__icontains": subject.model_name, **year_filters}, 4, "Aynı marka, model ve yakın yıl", 5)
        add({**exact, "brand__iexact": subject.brand, "model_name__icontains": subject.model_name}, 4, "Aynı marka ve model", 5)
    if brand:
        add({**exact, "brand__iexact": subject.brand, **year_filters}, 5, "Aynı marka ve yakın model yılı", 4)
        add({**exact, "brand__iexact": subject.brand}, 6, "Aynı marka ve araç kategorisi", 3)
    if year_filters:
        add({**exact, **year_filters}, 6, "Aynı araç kategorisi ve yakın model yılı", 3)
    add(exact, 7, "Aynı araç kategorisi", 2)
    add(root, 10, "Yakın araç kategorisi", 1)
    return plans


def _estate_plans(subject: Listing) -> list[_CandidatePlan]:
    exact, root = _category_filters(subject)
    plans: list[_CandidatePlan] = []

    def add(filters: dict, minimum: int, label: str, specificity: int) -> None:
        plans.append(_CandidatePlan(filters=filters, minimum=minimum, label=label, specificity=specificity))

    area_tight = {}
    area_wide = {}
    if subject.area_m2:
        area_tight = {
            "area_m2__gte": max(1, int(subject.area_m2 * 0.75)),
            "area_m2__lte": int(subject.area_m2 * 1.25) + 1,
        }
        area_wide = {
            "area_m2__gte": max(1, int(subject.area_m2 * 0.60)),
            "area_m2__lte": int(subject.area_m2 * 1.45) + 1,
        }
    room = {"room_count__iexact": subject.room_count} if subject.room_count else {}
    city = {"city__iexact": subject.city} if subject.city else {}
    district = {"district__iexact": subject.district} if subject.district else {}
    neighborhood = {"neighborhood__iexact": subject.neighborhood} if subject.neighborhood else {}

    if neighborhood:
        add({**exact, **city, **district, **neighborhood, **room, **area_tight}, 4, "Aynı mahalle ve benzer emlak özellikleri", 5)
    if district:
        add({**exact, **city, **district, **room, **area_tight}, 4, "Aynı ilçe, oda ve yakın metrekare", 5)
        add({**exact, **city, **district, **area_wide}, 4, "Aynı ilçe ve yakın metrekare", 4)
    if city:
        add({**exact, **city, **room, **area_tight}, 5, "Aynı şehir, oda ve yakın metrekare", 4)
        add({**exact, **city, **area_wide}, 5, "Aynı şehir ve yakın metrekare", 3)
        add({**exact, **city}, 6, "Aynı şehir ve emlak kategorisi", 3)
        add({**root, **city, **district}, 6, "Aynı bölge ve yakın emlak kategorisi", 2)
        add({**root, **city}, 8, "Aynı şehir ve yakın emlak kategorisi", 1)
    return plans


def _query_prices(queryset: QuerySet, plan: _CandidatePlan) -> list[Decimal]:
    filters = dict(plan.filters)
    root_q = filters.pop("_root_q", None)
    if root_q is not None:
        queryset = queryset.filter(root_q)
    queryset = queryset.filter(**filters)
    return [Decimal(value) for value in queryset.order_by("-published_at").values_list("price", flat=True)[:160]]


def _confidence(sample_count: int, specificity: int) -> tuple[str, str]:
    if sample_count >= 12 and specificity >= 3:
        return "high", "Yüksek güven"
    if sample_count >= 6 and specificity >= 2:
        return "medium", "Orta güven"
    return "low", "Sınırlı veri"


def _unavailable(message: str) -> PriceGuide:
    return PriceGuide(available=False, message=message)


def build_price_guide(subject: Listing, *, exclude_pk: int | None = None) -> PriceGuide:
    """Yayındaki benzer ilanlardan açıklanabilir ve dayanıklı bir fiyat özeti üretir.

    Rehber yalnız İlan Şehri'ndeki aktif ilan fiyatlarını karşılaştırır. Bir ekspertiz,
    değerleme veya satış garantisi değildir. Aynı kullanıcının ilanları dışarıda bırakılır
    ve aşırı uç fiyatlar istatistikten temizlenir.
    """

    if subject.kind not in SUPPORTED_KINDS:
        return _unavailable("Fiyat rehberi şu anda ürün, araç ve emlak ilanlarında kullanılabilir.")
    if subject.action not in SUPPORTED_ACTIONS:
        return _unavailable("Fiyat rehberi satılık ve kiralık ilanlar için hesaplanır.")
    if not subject.category_id:
        return _unavailable("Önce ilan kategorisini seç.")

    plans = {
        Listing.Kind.PRODUCT: _product_plans,
        Listing.Kind.VEHICLE: _vehicle_plans,
        Listing.Kind.REAL_ESTATE: _estate_plans,
    }[subject.kind](subject)
    base = _active_price_queryset(subject, exclude_pk=exclude_pk)

    selected_prices: list[Decimal] = []
    selected_plan: _CandidatePlan | None = None
    for plan in plans:
        prices = _query_prices(base, plan)
        if len(prices) >= plan.minimum:
            selected_prices = prices
            selected_plan = plan
            break

    if not selected_plan:
        return _unavailable("Güvenilir bir aralık için yeterli benzer ilan henüz bulunmuyor.")

    cleaned, removed = _remove_outliers(selected_prices)
    if len(cleaned) < 4:
        return _unavailable("Benzer ilan sayısı güvenilir bir fiyat aralığı oluşturmaya yetmiyor.")

    median_raw = _percentile(cleaned, Decimal("0.50"))
    lower_raw = _percentile(cleaned, Decimal("0.25"))
    upper_raw = _percentile(cleaned, Decimal("0.75"))
    if upper_raw <= lower_raw or upper_raw < median_raw * Decimal("1.08"):
        lower_raw = median_raw * Decimal("0.90")
        upper_raw = median_raw * Decimal("1.10")

    lower = _round_market(lower_raw, direction="down")
    median = _round_market(median_raw, direction="nearest")
    upper = _round_market(upper_raw, direction="up")
    if lower <= 0:
        lower = _market_step(median)
    if upper <= lower:
        upper = lower + (_market_step(median) * 2)

    status = "no_price"
    status_label = "Fiyat girişi bekleniyor"
    if subject.price is not None and subject.price > 0:
        price = Decimal(subject.price)
        if price < lower * Decimal("0.90"):
            status = "low"
            status_label = "Piyasanın altında"
        elif price > upper * Decimal("1.10"):
            status = "high"
            status_label = "Piyasanın üzerinde"
        else:
            status = "fair"
            status_label = "Piyasa aralığında"

    confidence, confidence_label = _confidence(len(cleaned), selected_plan.specificity)
    criteria = [selected_plan.label, "Yalnız aktif ve fiyatlı ilanlar"]
    if removed:
        criteria.append(f"{removed} uç fiyat hesaptan çıkarıldı")
    criteria.append("Aynı satıcının diğer ilanları dahil edilmedi")

    return PriceGuide(
        available=True,
        sample_count=len(cleaned),
        lower_price=lower,
        median_price=median,
        upper_price=upper,
        status=status,
        status_label=status_label,
        confidence=confidence,
        confidence_label=confidence_label,
        message="Bu aralık İlan Şehri'ndeki benzer ilanlardan hesaplanan tahmini bir rehberdir; ekspertiz veya satış garantisi değildir.",
        criteria=tuple(criteria),
        removed_outliers=removed,
    )
