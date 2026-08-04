from django.conf import settings
from django.db import models


class ManagedRequest(models.Model):
    class Package(models.TextChoices):
        DIGITAL = "digital", "Dijital Asistan"
        ON_SITE = "on_site", "Yerinde Destek"
        FULL = "full", "Tam Yönetim"

    class Status(models.TextChoices):
        NEW = "new", "Yeni"
        REVIEW = "review", "İncelemede"
        ACTIVE = "active", "Aktif"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal"

    listing = models.OneToOneField("listings.Listing", related_name="managed_request", on_delete=models.CASCADE)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="managed_requests", on_delete=models.CASCADE)
    package = models.CharField(max_length=20, choices=Package.choices, default=Package.DIGITAL)
    requested_services = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.listing.title} - {self.get_package_display()}"
