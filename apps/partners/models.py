from django.conf import settings
from django.db import models


class PartnerProfile(models.Model):
    class Level(models.TextChoices):
        STARTER = "starter", "Başlangıç"
        VERIFIED = "verified", "Doğrulanmış Görev Ortağı"
        PROFESSIONAL = "professional", "Profesyonel İlan Yöneticisi"
        AUTHORIZED = "authorized", "Yetkili Çözüm Ortağı"

    class Status(models.TextChoices):
        PENDING = "pending", "Başvuru"
        ACTIVE = "active", "Aktif"
        SUSPENDED = "suspended", "Askıda"
        REJECTED = "rejected", "Reddedildi"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="partner_profile", on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.STARTER)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    skills = models.JSONField(default=list, blank=True)
    service_cities = models.JSONField(default=list, blank=True)
    identity_verified = models.BooleanField(default=False)
    professional_documents_verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user} - {self.get_level_display()}"


class Task(models.Model):
    class TaskType(models.TextChoices):
        PHOTO = "photo", "Fotoğraf / Video Çekimi"
        LISTING_PREP = "listing_prep", "İlan Hazırlama"
        PRICE_RESEARCH = "price_research", "Fiyat Araştırması"
        MESSAGE_MANAGEMENT = "message_management", "Mesaj Yönetimi"
        OFFER_COLLECTION = "offer_collection", "Teklif Toplama"
        APPOINTMENT = "appointment", "Randevu Organizasyonu"
        SHOWING = "showing", "Yerinde Gösterim"

    class Status(models.TextChoices):
        OPEN = "open", "Açık"
        ASSIGNED = "assigned", "Atandı"
        IN_PROGRESS = "in_progress", "Devam Ediyor"
        REVIEW = "review", "Kontrolde"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal"

    managed_request = models.ForeignKey("managed_services.ManagedRequest", related_name="tasks", on_delete=models.CASCADE)
    assigned_partner = models.ForeignKey(PartnerProfile, null=True, blank=True, related_name="tasks", on_delete=models.SET_NULL)
    task_type = models.CharField(max_length=30, choices=TaskType.choices)
    description = models.TextField()
    city = models.CharField(max_length=80)
    district = models.CharField(max_length=80)
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    success_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.get_task_type_display()} - {self.city}/{self.district}"
