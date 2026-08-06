from __future__ import annotations

from datetime import timedelta

import hashlib
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )
    icon = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name_plural = "Kategoriler"

    def __str__(self) -> str:
        return self.name


class Listing(models.Model):
    class Kind(models.TextChoices):
        PRODUCT = "product", "Ürün / Eşya"
        VEHICLE = "vehicle", "Araç"
        REAL_ESTATE = "real_estate", "Emlak"
        SERVICE = "service", "Hizmet"
        NEED = "need", "İhtiyaç / Arıyorum"
        JOB = "job", "İş"

    class Action(models.TextChoices):
        SELL = "sell", "Satılık"
        RENT = "rent", "Kiralık"
        SWAP = "swap", "Takas"
        WANTED = "wanted", "Arıyorum"
        SERVICE_OFFER = "service_offer", "Hizmet Veriyorum"
        SERVICE_REQUEST = "service_request", "Hizmet Arıyorum"
        JOB_OFFER = "job_offer", "Çalışan Arıyorum"
        JOB_REQUEST = "job_request", "İş Arıyorum"

    class ManagementMode(models.TextChoices):
        SELF = "self", "Kendim yöneteceğim"
        FULL = "full", "İlan Şehri yönetsin"

    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        REVIEW = "review", "İncelemede"
        PUBLISHED = "published", "Yayında"
        PAUSED = "paused", "Duraklatıldı"
        COMPLETED = "completed", "Sonuçlandı"
        REJECTED = "rejected", "Reddedildi"
        EXPIRED = "expired", "Süresi doldu"

    class FuelType(models.TextChoices):
        GASOLINE = "gasoline", "Benzin"
        DIESEL = "diesel", "Dizel"
        LPG = "lpg", "LPG"
        HYBRID = "hybrid", "Hibrit"
        ELECTRIC = "electric", "Elektrik"
        OTHER = "other", "Diğer"

    class Transmission(models.TextChoices):
        AUTOMATIC = "automatic", "Otomatik"
        MANUAL = "manual", "Manuel"
        SEMI_AUTOMATIC = "semi_automatic", "Yarı otomatik"

    class FeeType(models.TextChoices):
        FIXED = "fixed", "Sabit ücret"
        HOURLY = "hourly", "Saatlik"
        DAILY = "daily", "Günlük"
        MONTHLY = "monthly", "Aylık"
        NEGOTIABLE = "negotiable", "Görüşülür"

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Tam zamanlı"
        PART_TIME = "part_time", "Yarı zamanlı"
        DAILY = "daily", "Günlük / dönemsel"
        REMOTE = "remote", "Uzaktan"
        INTERNSHIP = "internship", "Staj"

    class DeliveryType(models.TextChoices):
        HANDOVER = "handover", "Elden teslim"
        SHIPPING = "shipping", "Kargo"
        ON_SITE = "on_site", "Yerinde hizmet / teslim"
        DIGITAL = "digital", "Dijital teslim"
        NEGOTIABLE = "negotiable", "Görüşülür"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="listings",
        on_delete=models.CASCADE,
    )
    category = models.ForeignKey(
        Category,
        related_name="listings",
        on_delete=models.PROTECT,
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    action = models.CharField(max_length=24, choices=Action.choices)
    management_mode = models.CharField(
        max_length=10,
        choices=ManagementMode.choices,
        default=ManagementMode.SELF,
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=210, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_on_request = models.BooleanField(default=False)
    is_negotiable = models.BooleanField(default=False)
    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices,
        blank=True,
        default="",
    )
    condition = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=60, blank=True, default="")
    search_tags = models.JSONField(default=list, blank=True)
    technical_features = models.JSONField(default=list, blank=True)

    brand = models.CharField(max_length=100, blank=True, default="")
    model_name = models.CharField(max_length=100, blank=True, default="")
    model_year = models.PositiveSmallIntegerField(null=True, blank=True)
    mileage = models.PositiveIntegerField(null=True, blank=True)
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices, blank=True, default="")
    transmission = models.CharField(max_length=20, choices=Transmission.choices, blank=True, default="")
    room_count = models.CharField(max_length=30, blank=True, default="")
    area_m2 = models.PositiveIntegerField(null=True, blank=True)
    building_age = models.PositiveSmallIntegerField(null=True, blank=True)
    floor_location = models.CharField(max_length=60, blank=True, default="")
    heating_type = models.CharField(max_length=80, blank=True, default="")
    service_area = models.CharField(max_length=160, blank=True, default="")
    fee_type = models.CharField(max_length=20, choices=FeeType.choices, blank=True, default="")
    job_type = models.CharField(max_length=20, choices=JobType.choices, blank=True, default="")
    experience_level = models.CharField(max_length=80, blank=True, default="")

    city = models.CharField(max_length=80)
    district = models.CharField(max_length=80)
    neighborhood = models.CharField(max_length=120, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REVIEW)
    review_note = models.TextField(blank=True, default="")
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="moderated_listings",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    favorite_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    renewal_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_featured", "-published_at", "-created_at")
        indexes = [
            models.Index(fields=["status", "kind", "action"]),
            models.Index(fields=["city", "district"]),
            models.Index(fields=["brand", "model_name"]),
            models.Index(fields=["-created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:180] or "ilan"
            candidate = base
            counter = 2
            while Listing.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{counter}"
                counter += 1
            self.slug = candidate
        if self.status == self.Status.PUBLISHED:
            if self.published_at is None:
                self.published_at = timezone.now()
            if self.expires_at is None:
                self.expires_at = timezone.now() + timedelta(days=60)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("listings:detail", kwargs={"slug": self.slug})

    @property
    def cover_image(self):
        prefetched = list(self.images.all())
        return next((image for image in prefetched if image.is_cover), prefetched[0] if prefetched else None)

    @property
    def location_text(self) -> str:
        return " / ".join(item for item in (self.city, self.district, self.neighborhood) if item)

    @property
    def detail_items(self):
        items = []
        if self.kind in {self.Kind.PRODUCT, self.Kind.VEHICLE}:
            if self.brand:
                items.append(("Marka", self.brand))
            if self.model_name:
                items.append(("Model", self.model_name))
            if self.condition:
                items.append(("Durum", self.condition))
            if self.color:
                items.append(("Renk", self.color))
        if self.kind == self.Kind.VEHICLE:
            if self.model_year:
                items.append(("Model yılı", self.model_year))
            if self.mileage is not None:
                items.append(("Kilometre", f"{self.mileage:,} km".replace(",", ".")))
            if self.fuel_type:
                items.append(("Yakıt", self.get_fuel_type_display()))
            if self.transmission:
                items.append(("Vites", self.get_transmission_display()))
        if self.kind == self.Kind.REAL_ESTATE:
            if self.room_count:
                items.append(("Oda sayısı", self.room_count))
            if self.area_m2:
                items.append(("Brüt alan", f"{self.area_m2} m²"))
            if self.building_age is not None:
                items.append(("Bina yaşı", self.building_age))
            if self.floor_location:
                items.append(("Bulunduğu kat", self.floor_location))
            if self.heating_type:
                items.append(("Isıtma", self.heating_type))
        if self.kind == self.Kind.SERVICE:
            if self.service_area:
                items.append(("Hizmet bölgesi", self.service_area))
            if self.fee_type:
                items.append(("Ücret tipi", self.get_fee_type_display()))
        if self.kind == self.Kind.JOB:
            if self.job_type:
                items.append(("Çalışma şekli", self.get_job_type_display()))
            if self.experience_level:
                items.append(("Deneyim", self.experience_level))
        if self.delivery_type:
            items.append(("Teslim / hizmet", self.get_delivery_type_display()))
        return items

    @property
    def latest_price_change(self):
        cached = getattr(self, "_prefetched_objects_cache", {}).get("price_history")
        if cached is not None:
            return cached[0] if cached else None
        return self.price_history.first()

    @property
    def price_drop_percent(self) -> int:
        change = self.latest_price_change
        if not change or change.old_price <= 0 or change.new_price >= change.old_price:
            return 0
        return round(((change.old_price - change.new_price) / change.old_price) * 100)

    def __str__(self) -> str:
        return self.title


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="listings/%Y/%m/")
    alt_text = models.CharField(max_length=180, blank=True)
    fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")

    def save(self, *args, **kwargs):
        if self.image and not self.fingerprint:
            try:
                file_obj = self.image.file
                position = file_obj.tell() if hasattr(file_obj, "tell") else None
                content = file_obj.read()
                self.fingerprint = hashlib.sha256(content).hexdigest()
                if hasattr(file_obj, "seek"):
                    file_obj.seek(position or 0)
            except (OSError, ValueError):
                self.fingerprint = ""
        super().save(*args, **kwargs)

    @property
    def duplicate_owner_count(self) -> int:
        if not self.fingerprint:
            return 0
        return (
            ListingImage.objects.filter(fingerprint=self.fingerprint)
            .exclude(listing__owner_id=self.listing.owner_id)
            .values("listing__owner_id")
            .distinct()
            .count()
        )

    def __str__(self) -> str:
        return f"{self.listing} · görsel {self.pk}"


class ListingPriceHistory(models.Model):
    listing = models.ForeignKey(
        Listing,
        related_name="price_history",
        on_delete=models.CASCADE,
    )
    old_price = models.DecimalField(max_digits=14, decimal_places=2)
    new_price = models.DecimalField(max_digits=14, decimal_places=2)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="listing_price_changes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notifications_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["listing", "-created_at"])]

    @property
    def is_drop(self) -> bool:
        return self.new_price < self.old_price

    def __str__(self) -> str:
        return f"{self.listing} · {self.old_price} → {self.new_price}"


class Offer(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Bekliyor"
        ACCEPTED = "accepted", "Kabul edildi"
        REJECTED = "rejected", "Reddedildi"
        WITHDRAWN = "withdrawn", "Geri çekildi"

    listing = models.ForeignKey(Listing, related_name="offers", on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="offers", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    message = models.TextField(max_length=1200)
    last_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="last_acted_offers",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    counter_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["listing", "status", "-created_at"])]

    @property
    def current_actor_id(self):
        return self.last_actor_id or self.sender_id

    @property
    def current_recipient_id(self):
        return self.sender_id if self.current_actor_id == self.listing.owner_id else self.listing.owner_id

    def can_respond(self, user) -> bool:
        return self.status == self.Status.PENDING and user.pk == self.current_recipient_id

    def other_participant(self, user):
        return self.listing.owner if user.pk == self.sender_id else self.sender

    def __str__(self) -> str:
        return f"{self.listing} · {self.sender}"


class OfferEvent(models.Model):
    class Type(models.TextChoices):
        SUBMITTED = "submitted", "Teklif gönderildi"
        COUNTERED = "countered", "Karşı teklif gönderildi"
        ACCEPTED = "accepted", "Teklif kabul edildi"
        REJECTED = "rejected", "Teklif reddedildi"
        WITHDRAWN = "withdrawn", "Teklif geri çekildi"

    offer = models.ForeignKey(Offer, related_name="events", on_delete=models.CASCADE)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="offer_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=16, choices=Type.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    message = models.TextField(max_length=1200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=["offer", "created_at"])]

    def __str__(self) -> str:
        return f"{self.offer} · {self.get_event_type_display()}"


class Transaction(models.Model):
    class Status(models.TextChoices):
        AGREED = "agreed", "Anlaşma sağlandı"
        DELIVERY = "delivery", "Teslim / hizmet aşamasında"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal edildi"
        DISPUTED = "disputed", "Uyuşmazlık bildirildi"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    listing = models.ForeignKey(Listing, related_name="transactions", on_delete=models.PROTECT)
    offer = models.OneToOneField(Offer, related_name="transaction", on_delete=models.PROTECT)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="purchases", on_delete=models.PROTECT)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sales", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.AGREED)
    delivery_type = models.CharField(
        max_length=20, choices=Listing.DeliveryType.choices, blank=True, default=""
    )
    delivery_started_at = models.DateTimeField(null=True, blank=True)
    handover_code_hash = models.CharField(max_length=128, blank=True, default="")
    handover_code_created_at = models.DateTimeField(null=True, blank=True)
    handover_code_attempts = models.PositiveSmallIntegerField(default=0)
    handover_verified_at = models.DateTimeField(null=True, blank=True)
    buyer_confirmed = models.BooleanField(default=False)
    seller_confirmed = models.BooleanField(default=False)
    buyer_confirmed_at = models.DateTimeField(null=True, blank=True)
    seller_confirmed_at = models.DateTimeField(null=True, blank=True)
    dispute_reason = models.TextField(max_length=1500, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(buyer=models.F("seller")),
                name="prevent_self_transaction",
            )
        ]

    def get_absolute_url(self):
        return reverse("listings:transaction_detail", kwargs={"public_id": self.public_id})

    def is_participant(self, user) -> bool:
        return user.pk in {self.buyer_id, self.seller_id}

    @property
    def requires_handover_code(self) -> bool:
        return self.delivery_type in {Listing.DeliveryType.HANDOVER, Listing.DeliveryType.ON_SITE}

    @property
    def handover_code_is_active(self) -> bool:
        return bool(
            self.handover_code_hash
            and self.handover_code_created_at
            and self.handover_code_created_at >= timezone.now() - timedelta(minutes=15)
            and self.handover_code_attempts < 5
            and not self.handover_verified_at
        )

    def __str__(self) -> str:
        return f"{self.listing} · {self.get_status_display()}"


class TransactionEvent(models.Model):
    class Type(models.TextChoices):
        CREATED = "created", "İşlem oluşturuldu"
        DELIVERY_STARTED = "delivery_started", "Teslim aşaması başladı"
        CODE_CREATED = "code_created", "Teslim kodu oluşturuldu"
        HANDOVER_VERIFIED = "handover_verified", "Teslim kodu doğrulandı"
        BUYER_CONFIRMED = "buyer_confirmed", "Alıcı tamamlamayı onayladı"
        SELLER_CONFIRMED = "seller_confirmed", "Satıcı tamamlamayı onayladı"
        COMPLETED = "completed", "İşlem tamamlandı"
        CANCELLED = "cancelled", "İşlem iptal edildi"
        DISPUTED = "disputed", "Uyuşmazlık açıldı"
        MODERATED = "moderated", "Destek ekibi sonuçlandırdı"

    transaction = models.ForeignKey(Transaction, related_name="events", on_delete=models.CASCADE)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="transaction_events", on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    event_type = models.CharField(max_length=24, choices=Type.choices)
    note = models.CharField(max_length=240, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=["transaction", "created_at"])]

    def __str__(self) -> str:
        return f"{self.transaction} · {self.get_event_type_display()}"


class Review(models.Model):
    transaction = models.ForeignKey(Transaction, related_name="reviews", on_delete=models.CASCADE)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="written_reviews", on_delete=models.CASCADE)
    reviewed_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="received_reviews", on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=1000, blank=True)
    is_visible = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("transaction", "reviewer"), name="unique_transaction_reviewer"),
            models.CheckConstraint(
                condition=~models.Q(reviewer=models.F("reviewed_user")),
                name="prevent_self_review",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.reviewed_user} · {self.rating}/5"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="favorite_items", on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, related_name="favorited_by", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "listing"), name="unique_user_listing_favorite")
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.listing}"


class SavedSearch(models.Model):
    class AlertFrequency(models.TextChoices):
        OFF = "off", "Kapalı"
        INSTANT = "instant", "Anlık"
        DAILY = "daily", "Günlük özet"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="saved_searches", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    query_params = models.JSONField(default=dict)
    alert_enabled = models.BooleanField(default=True)
    alert_frequency = models.CharField(
        max_length=12,
        choices=AlertFrequency.choices,
        default=AlertFrequency.INSTANT,
    )
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["alert_enabled", "alert_frequency", "last_checked_at"])]

    def save(self, *args, **kwargs):
        self.name = (self.name or "").strip()[:120]
        self.alert_enabled = self.alert_frequency != self.AlertFrequency.OFF
        super().save(*args, **kwargs)

    @property
    def effective_alert_frequency(self):
        return self.alert_frequency if self.alert_enabled else self.AlertFrequency.OFF

    def __str__(self) -> str:
        return f"{self.user} · {self.name}"


class SavedSearchMatch(models.Model):
    saved_search = models.ForeignKey(SavedSearch, related_name="matches", on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, related_name="saved_search_matches", on_delete=models.CASCADE)
    notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("saved_search", "listing"),
                name="unique_saved_search_listing_match",
            )
        ]
        indexes = [models.Index(fields=["saved_search", "notified_at", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.saved_search} · {self.listing}"


class ListingMatch(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yeni"
        VIEWED = "viewed", "Görüldü"
        DISMISSED = "dismissed", "Gizlendi"

    wanted_listing = models.ForeignKey(
        Listing,
        related_name="wanted_matches",
        on_delete=models.CASCADE,
    )
    offered_listing = models.ForeignKey(
        Listing,
        related_name="offered_matches",
        on_delete=models.CASCADE,
    )
    score = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    reasons = models.JSONField(default=list, blank=True)
    wanted_status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.NEW,
    )
    offered_status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.NEW,
    )
    notified_wanted_at = models.DateTimeField(null=True, blank=True)
    notified_offered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-score", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("wanted_listing", "offered_listing"),
                name="unique_wanted_offered_listing_match",
            )
        ]
        indexes = [
            models.Index(fields=["wanted_listing", "wanted_status", "-score"]),
            models.Index(fields=["offered_listing", "offered_status", "-score"]),
        ]
        verbose_name = "İlan Eşleşmesi"
        verbose_name_plural = "İlan Eşleşmeleri"

    def __str__(self) -> str:
        return f"{self.wanted_listing} ↔ {self.offered_listing} · %{self.score}"


class ListingDraft(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="listing_drafts",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=180, blank=True)
    data = models.JSONField(default=dict)
    source_listing = models.ForeignKey(
        Listing,
        related_name="draft_revisions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [models.Index(fields=["user", "-updated_at"])]

    @property
    def display_title(self) -> str:
        return self.title.strip() or "İsimsiz taslak"

    def __str__(self) -> str:
        return f"{self.user} · {self.display_title}"


class Conversation(models.Model):
    listing = models.ForeignKey(Listing, related_name="conversations", on_delete=models.CASCADE)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="buying_conversations", on_delete=models.CASCADE)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="selling_conversations", on_delete=models.CASCADE)
    buyer_archived = models.BooleanField(default=False)
    seller_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(fields=("listing", "buyer"), name="unique_listing_buyer_conversation")
        ]

    def other_participant(self, user):
        return self.seller if user.pk == self.buyer_id else self.buyer

    def __str__(self) -> str:
        return f"{self.listing} · {self.buyer} / {self.seller}"


class Appointment(models.Model):
    class Type(models.TextChoices):
        IN_PERSON = "in_person", "Yüz yüze görüşme"
        PHONE = "phone", "Telefon görüşmesi"
        VIDEO = "video", "Görüntülü görüşme"
        DELIVERY = "delivery", "Teslim / hizmet randevusu"

    class Status(models.TextChoices):
        PENDING = "pending", "Yanıt bekliyor"
        ACCEPTED = "accepted", "Onaylandı"
        DECLINED = "declined", "Reddedildi"
        CANCELLED = "cancelled", "İptal edildi"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        related_name="appointments",
        on_delete=models.CASCADE,
    )
    listing = models.ForeignKey(
        Listing,
        related_name="appointments",
        on_delete=models.CASCADE,
    )
    proposer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="proposed_appointments",
        on_delete=models.CASCADE,
    )
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="received_appointments",
        on_delete=models.CASCADE,
    )
    appointment_type = models.CharField(max_length=16, choices=Type.choices)
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    city = models.CharField(max_length=80, blank=True)
    district = models.CharField(max_length=80, blank=True)
    place = models.CharField(max_length=180, blank=True)
    note = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("starts_at", "-created_at")
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(proposer=models.F("invitee")),
                name="prevent_self_appointment",
            )
        ]
        indexes = [
            models.Index(fields=["status", "starts_at"]),
            models.Index(fields=["invitee", "status", "starts_at"]),
            models.Index(fields=["proposer", "status", "starts_at"]),
        ]

    def get_absolute_url(self):
        return reverse("listings:appointment_list") + f"?highlight={self.public_id}"

    def is_participant(self, user) -> bool:
        return bool(user.is_authenticated and user.pk in {self.proposer_id, self.invitee_id})

    def other_participant(self, user):
        return self.invitee if user.pk == self.proposer_id else self.proposer

    @property
    def is_upcoming(self) -> bool:
        return self.status == self.Status.ACCEPTED and self.starts_at >= timezone.now()

    @property
    def location_text(self) -> str:
        parts = [item for item in (self.city, self.district, self.place) if item]
        return " / ".join(parts)

    def __str__(self) -> str:
        return f"{self.listing} · {self.get_appointment_type_display()} · {self.starts_at:%d.%m.%Y %H:%M}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sent_listing_messages", on_delete=models.CASCADE)
    body = models.TextField(max_length=1600)
    attachment = models.ImageField(upload_to="messages/%Y/%m/", blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=["conversation", "is_read", "created_at"])]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Conversation.objects.filter(pk=self.conversation_id).update(updated_at=timezone.now())

    @property
    def safety_analysis(self):
        from .message_safety import analyze_message

        return analyze_message(self.body)

    def __str__(self) -> str:
        return f"{self.sender}: {self.body[:40]}"


class Notification(models.Model):
    class Type(models.TextChoices):
        MESSAGE = "message", "Mesaj"
        OFFER = "offer", "Teklif"
        TRANSACTION = "transaction", "İşlem"
        REVIEW = "review", "Puan / yorum"
        LISTING_STATUS = "listing_status", "İlan durumu"
        MANAGED = "managed", "Tam yönetim"
        TASK = "task", "Görev"
        VERIFICATION = "verification", "Doğrulama"
        PRICE_DROP = "price_drop", "Fiyat düşüşü"
        FOLLOW = "follow", "Satıcı takibi"
        MATCH = "match", "Akıllı eşleşme"
        SEARCH_ALERT = "search_alert", "Kayıtlı arama"
        SYSTEM = "system", "Sistem"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="notifications", on_delete=models.CASCADE)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="triggered_notifications",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    listing = models.ForeignKey(
        Listing,
        related_name="notifications",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notification_type = models.CharField(max_length=24, choices=Type.choices)
    title = models.CharField(max_length=180)
    body = models.CharField(max_length=320, blank=True)
    link = models.CharField(max_length=320, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "is_read", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user} · {self.title}"


class ListingReport(models.Model):
    class Reason(models.TextChoices):
        FRAUD = "fraud", "Dolandırıcılık şüphesi"
        WRONG_INFO = "wrong_info", "Yanlış / yanıltıcı bilgi"
        PROHIBITED = "prohibited", "Yasaklı ürün veya hizmet"
        DUPLICATE = "duplicate", "Tekrarlanan ilan"
        HARASSMENT = "harassment", "Uygunsuz iletişim"
        OTHER = "other", "Diğer"

    class Status(models.TextChoices):
        OPEN = "open", "Açık"
        REVIEWING = "reviewing", "İnceleniyor"
        RESOLVED = "resolved", "Çözüldü"
        DISMISSED = "dismissed", "İşlem gerektirmiyor"

    listing = models.ForeignKey(Listing, related_name="reports", on_delete=models.CASCADE)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="listing_reports", on_delete=models.CASCADE)
    reason = models.CharField(max_length=24, choices=Reason.choices)
    details = models.TextField(max_length=1200, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reviewed_listing_reports",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("listing", "reporter"), name="unique_listing_reporter")
        ]

    def __str__(self) -> str:
        return f"{self.listing} · {self.get_reason_display()}"
