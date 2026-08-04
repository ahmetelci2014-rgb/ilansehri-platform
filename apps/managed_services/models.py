from __future__ import annotations

from django.conf import settings
from django.db import models


class ManagedRequest(models.Model):
    class Package(models.TextChoices):
        DIGITAL = "digital", "Dijital Asistan"
        ON_SITE = "on_site", "Yerinde Destek"
        FULL = "full", "Tam Yönetim"

    class Status(models.TextChoices):
        NEW = "new", "Yeni talep"
        REVIEW = "review", "İhtiyaç analizi"
        QUOTED = "quoted", "Teklif sunuldu"
        ACTIVE = "active", "Aktif yönetim"
        WAITING_CUSTOMER = "waiting_customer", "Müşteri bekleniyor"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal"

    class ContactPreference(models.TextChoices):
        PHONE = "phone", "Telefon"
        MESSAGE = "message", "İlan Şehri mesajı"
        EMAIL = "email", "E-posta"

    listing = models.OneToOneField(
        "listings.Listing",
        related_name="managed_request",
        on_delete=models.CASCADE,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="managed_requests",
        on_delete=models.CASCADE,
    )
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_managed_requests",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"is_staff": True},
    )
    package = models.CharField(max_length=20, choices=Package.choices, default=Package.DIGITAL)
    requested_services = models.JSONField(default=list, blank=True)
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    preferred_contact = models.CharField(
        max_length=16,
        choices=ContactPreference.choices,
        default=ContactPreference.MESSAGE,
    )
    quote_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    success_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    progress = models.PositiveSmallIntegerField(default=0)
    next_action = models.CharField(max_length=240, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return f"{self.listing.title} - {self.get_package_display()}"


class ManagedActivity(models.Model):
    class ActivityType(models.TextChoices):
        NOTE = "note", "Not"
        CALL = "call", "Telefon görüşmesi"
        PHOTO = "photo", "Fotoğraf / video"
        PRICE = "price", "Fiyat araştırması"
        MESSAGE = "message", "Mesaj / teklif yönetimi"
        APPOINTMENT = "appointment", "Randevu"
        STATUS = "status", "Durum güncellemesi"

    managed_request = models.ForeignKey(
        ManagedRequest,
        related_name="activities",
        on_delete=models.CASCADE,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="managed_activities",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    activity_type = models.CharField(max_length=24, choices=ActivityType.choices, default=ActivityType.NOTE)
    note = models.TextField(max_length=1600)
    visible_to_customer = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "Tam yönetim aktiviteleri"

    def __str__(self) -> str:
        return f"{self.managed_request} · {self.get_activity_type_display()}"
