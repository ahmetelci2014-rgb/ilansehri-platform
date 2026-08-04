from django.conf import settings
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
    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_on_request = models.BooleanField(default=False)
    condition = models.CharField(max_length=50, blank=True)

    # Kategoriye özel yapılandırılmış alanlar
    brand = models.CharField(max_length=100, blank=True, default="")
    model_name = models.CharField(max_length=100, blank=True, default="")
    model_year = models.PositiveSmallIntegerField(null=True, blank=True)
    mileage = models.PositiveIntegerField(null=True, blank=True)
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices, blank=True, default="")
    transmission = models.CharField(
        max_length=20,
        choices=Transmission.choices,
        blank=True,
        default="",
    )
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
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.REVIEW,
    )
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
    published_at = models.DateTimeField(null=True, blank=True)
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
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("listings:detail", kwargs={"slug": self.slug})

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
        return items

    def __str__(self) -> str:
        return self.title


class ListingImage(models.Model):
    listing = models.ForeignKey(
        Listing,
        related_name="images",
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to="listings/%Y/%m/")
    alt_text = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)

    class Meta:
        ordering = ("sort_order", "id")


class Offer(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Bekliyor"
        ACCEPTED = "accepted", "Kabul edildi"
        REJECTED = "rejected", "Reddedildi"
        WITHDRAWN = "withdrawn", "Geri çekildi"

    listing = models.ForeignKey(
        Listing,
        related_name="offers",
        on_delete=models.CASCADE,
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="offers",
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    message = models.TextField(max_length=1200)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="favorite_items",
        on_delete=models.CASCADE,
    )
    listing = models.ForeignKey(
        Listing,
        related_name="favorited_by",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "listing"),
                name="unique_user_listing_favorite",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.listing}"


class Conversation(models.Model):
    listing = models.ForeignKey(
        Listing,
        related_name="conversations",
        on_delete=models.CASCADE,
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="buying_conversations",
        on_delete=models.CASCADE,
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="selling_conversations",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "buyer"),
                name="unique_listing_buyer_conversation",
            )
        ]

    def other_participant(self, user):
        return self.seller if user == self.buyer else self.buyer

    def __str__(self) -> str:
        return f"{self.listing} · {self.buyer} / {self.seller}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="sent_listing_messages",
        on_delete=models.CASCADE,
    )
    body = models.TextField(max_length=1600)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["conversation", "is_read", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Conversation.objects.filter(pk=self.conversation_id).update(
            updated_at=timezone.now()
        )

    def __str__(self) -> str:
        return f"{self.sender}: {self.body[:40]}"


class Notification(models.Model):
    class Type(models.TextChoices):
        MESSAGE = "message", "Mesaj"
        OFFER = "offer", "Teklif"
        LISTING_STATUS = "listing_status", "İlan durumu"
        SYSTEM = "system", "Sistem"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="notifications",
        on_delete=models.CASCADE,
    )
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
        on_delete=models.CASCADE,
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

    listing = models.ForeignKey(
        Listing,
        related_name="reports",
        on_delete=models.CASCADE,
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="listing_reports",
        on_delete=models.CASCADE,
    )
    reason = models.CharField(max_length=24, choices=Reason.choices)
    details = models.TextField(max_length=1200, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
    )
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
            models.UniqueConstraint(
                fields=("listing", "reporter"),
                name="unique_listing_reporter",
            )
        ]

    def __str__(self) -> str:
        return f"{self.listing} · {self.get_reason_display()}"
