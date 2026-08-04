from __future__ import annotations

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

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="partner_profile",
        on_delete=models.CASCADE,
    )
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.STARTER)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    about = models.TextField(max_length=800, blank=True)
    skills = models.JSONField(default=list, blank=True)
    service_cities = models.JSONField(default=list, blank=True)
    available = models.BooleanField(default=True)
    identity_verified = models.BooleanField(default=False)
    professional_documents_verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

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
        DELIVERY = "delivery", "Teslim Desteği"

    class Status(models.TextChoices):
        OPEN = "open", "Açık"
        ASSIGNED = "assigned", "Atandı"
        IN_PROGRESS = "in_progress", "Devam Ediyor"
        REVIEW = "review", "Kontrolde"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal"

    managed_request = models.ForeignKey(
        "managed_services.ManagedRequest",
        related_name="tasks",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=180)
    task_type = models.CharField(max_length=30, choices=TaskType.choices)
    description = models.TextField()
    city = models.CharField(max_length=80)
    district = models.CharField(max_length=80)
    min_level = models.CharField(
        max_length=20,
        choices=PartnerProfile.Level.choices,
        default=PartnerProfile.Level.STARTER,
    )
    assigned_partner = models.ForeignKey(
        PartnerProfile,
        null=True,
        blank=True,
        related_name="tasks",
        on_delete=models.SET_NULL,
    )
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    success_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    result_note = models.TextField(blank=True)
    proof_file = models.FileField(upload_to="task-proofs/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "city", "task_type"])]

    def __str__(self) -> str:
        return f"{self.title} - {self.city}/{self.district}"


class TaskApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Bekliyor"
        ACCEPTED = "accepted", "Kabul edildi"
        REJECTED = "rejected", "Reddedildi"
        WITHDRAWN = "withdrawn", "Geri çekildi"

    task = models.ForeignKey(Task, related_name="applications", on_delete=models.CASCADE)
    partner = models.ForeignKey(PartnerProfile, related_name="task_applications", on_delete=models.CASCADE)
    note = models.TextField(max_length=700, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("task", "partner"), name="unique_task_partner_application")
        ]

    def __str__(self) -> str:
        return f"{self.task} · {self.partner}"


class PartnerEarning(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Bekliyor"
        APPROVED = "approved", "Onaylandı"
        PAID = "paid", "Ödendi"
        CANCELLED = "cancelled", "İptal"

    partner = models.ForeignKey(PartnerProfile, related_name="earnings", on_delete=models.CASCADE)
    task = models.OneToOneField(Task, related_name="earning", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.partner} · {self.amount} TL"
