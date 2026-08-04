from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.CASCADE)
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

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="listings", on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name="listings", on_delete=models.PROTECT)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    action = models.CharField(max_length=24, choices=Action.choices)
    management_mode = models.CharField(max_length=10, choices=ManagementMode.choices, default=ManagementMode.SELF)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=210, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_on_request = models.BooleanField(default=False)
    condition = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=80)
    district = models.CharField(max_length=80)
    neighborhood = models.CharField(max_length=120, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REVIEW)
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

    def __str__(self) -> str:
        return self.title


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, related_name="images", on_delete=models.CASCADE)
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

    listing = models.ForeignKey(Listing, related_name="offers", on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="offers", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    message = models.TextField(max_length=1200)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
