from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class SupportTicket(models.Model):
    class Category(models.TextChoices):
        ACCOUNT = "account", "Hesap ve doğrulama"
        LISTING = "listing", "İlan ve moderasyon"
        MESSAGE = "message", "Mesaj ve teklif"
        TRANSACTION = "transaction", "İşlem ve uyuşmazlık"
        MANAGED = "managed", "Tam Yönetim"
        PARTNER = "partner", "Kazanç Ağı"
        TECHNICAL = "technical", "Teknik sorun"
        OTHER = "other", "Diğer"

    class Priority(models.TextChoices):
        LOW = "low", "Düşük"
        NORMAL = "normal", "Normal"
        HIGH = "high", "Yüksek"
        URGENT = "urgent", "Acil"

    class Status(models.TextChoices):
        OPEN = "open", "Yeni"
        IN_PROGRESS = "in_progress", "İnceleniyor"
        WAITING_USER = "waiting_user", "Kullanıcı yanıtı bekleniyor"
        RESOLVED = "resolved", "Çözüldü"
        CLOSED = "closed", "Kapatıldı"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="support_tickets",
        on_delete=models.CASCADE,
    )
    category = models.CharField(max_length=24, choices=Category.choices)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    subject = models.CharField(max_length=180)
    description = models.TextField(max_length=4000)
    related_listing = models.ForeignKey(
        "listings.Listing",
        related_name="support_tickets",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    related_transaction = models.ForeignKey(
        "listings.Transaction",
        related_name="support_tickets",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_support_tickets",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"is_staff": True},
    )
    last_reply_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-created_at")
        indexes = [
            models.Index(fields=["user", "status", "-updated_at"]),
            models.Index(fields=["status", "priority", "-updated_at"]),
            models.Index(fields=["assigned_to", "status", "-updated_at"]),
        ]

    def get_absolute_url(self):
        return reverse("support_center:ticket_detail", kwargs={"public_id": self.public_id})

    @property
    def is_open(self) -> bool:
        return self.status not in {self.Status.RESOLVED, self.Status.CLOSED}

    def mark_resolved(self):
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at", "updated_at"])

    def __str__(self) -> str:
        return f"#{str(self.public_id)[:8]} · {self.subject}"


class SupportReply(models.Model):
    ticket = models.ForeignKey(SupportTicket, related_name="replies", on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="support_replies",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    message = models.TextField(max_length=4000)
    is_internal_note = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=["ticket", "created_at"])]

    def __str__(self) -> str:
        return f"{self.ticket} · {self.author or 'Sistem'}"


class StaffActionLog(models.Model):
    class Action(models.TextChoices):
        TICKET_CREATED = "ticket_created", "Destek talebi açıldı"
        TICKET_ASSIGNED = "ticket_assigned", "Destek talebi atandı"
        TICKET_REPLIED = "ticket_replied", "Destek yanıtı gönderildi"
        TICKET_STATUS = "ticket_status", "Destek durumu değişti"
        INTERNAL_NOTE = "internal_note", "İç not eklendi"
        LISTING_MODERATION = "listing_moderation", "İlan moderasyonu"
        ACCOUNT_ACTION = "account_action", "Hesap işlemi"
        OTHER = "other", "Diğer"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="staff_action_logs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    target_type = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=80, blank=True)
    summary = models.CharField(max_length=300)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["action", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.get_action_display()} · {self.summary}"
