from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class AISettings(models.Model):
    class Provider(models.TextChoices):
        MOCK = "mock", "Test sağlayıcısı"
        HTTP_JSON = "http_json", "Harici JSON görsel servisi"

    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    is_enabled = models.BooleanField(default=False, verbose_name="Özellik açık")
    provider = models.CharField(max_length=24, choices=Provider.choices, default=Provider.MOCK)
    model_name = models.CharField(max_length=120, blank=True, default="vision-model")
    user_daily_limit = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Kullanıcı başına günlük limit",
    )
    site_daily_limit = models.PositiveIntegerField(
        default=250,
        validators=[MinValueValidator(1), MaxValueValidator(100000)],
        verbose_name="Site geneli günlük limit",
    )
    timeout_seconds = models.PositiveSmallIntegerField(
        default=45,
        validators=[MinValueValidator(5), MaxValueValidator(180)],
    )
    max_images = models.PositiveSmallIntegerField(
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
    )
    max_image_size_mb = models.PositiveSmallIntegerField(
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    min_confidence_score = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    successful_analyses = models.PositiveIntegerField(default=0, editable=False)
    failed_analyses = models.PositiveIntegerField(default=0, editable=False)
    blocked_analyses = models.PositiveIntegerField(default=0, editable=False)
    total_duration_ms = models.PositiveBigIntegerField(default=0, editable=False)
    last_connection_checked_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_connection_ok = models.BooleanField(null=True, blank=True, editable=False)
    last_connection_message = models.CharField(max_length=500, blank=True, editable=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="updated_ai_settings",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        editable=False,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Yapay Zekâ Ayarı"
        verbose_name_plural = "Yapay Zekâ Ayarları"

    def clean(self):
        if self.user_daily_limit > self.site_daily_limit:
            raise ValidationError(
                {"user_daily_limit": "Kullanıcı limiti site geneli limitinden büyük olamaz."}
            )

    def save(self, *args, **kwargs):
        self.singleton_key = 1
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(singleton_key=1)
        return obj

    @property
    def total_analyses(self) -> int:
        return self.successful_analyses + self.failed_analyses + self.blocked_analyses

    @property
    def success_rate(self) -> float:
        total = self.total_analyses
        return round((self.successful_analyses / total) * 100, 1) if total else 0.0

    @property
    def average_duration_ms(self) -> int:
        completed = self.successful_analyses + self.failed_analyses + self.blocked_analyses
        return round(self.total_duration_ms / completed) if completed else 0

    def __str__(self) -> str:
        return "Yapay Zekâ İlan Asistanı Ayarları"


class AIAnalysis(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Bekliyor"
        PROCESSING = "processing", "İşleniyor"
        SUCCEEDED = "succeeded", "Başarılı"
        FAILED = "failed", "Başarısız"
        BLOCKED = "blocked", "Güvenlik nedeniyle engellendi"

    class SafetyStatus(models.TextChoices):
        SAFE = "safe", "Güvenli"
        REVIEW_REQUIRED = "review_required", "Kullanıcı onayı gerekli"
        BLOCKED = "blocked", "Engellendi"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="ai_listing_analyses",
        on_delete=models.CASCADE,
    )
    listing = models.ForeignKey(
        "listings.Listing",
        related_name="ai_analyses",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    safety_status = models.CharField(
        max_length=24,
        choices=SafetyStatus.choices,
        default=SafetyStatus.REVIEW_REQUIRED,
    )
    provider = models.CharField(max_length=24)
    model_name = models.CharField(max_length=120, blank=True)
    idempotency_key = models.CharField(max_length=80)
    request_hash = models.CharField(max_length=64, blank=True)
    image_count = models.PositiveSmallIntegerField(default=0)
    image_fingerprints = models.JSONField(default=list, blank=True)
    validated_output = models.JSONField(default=dict, blank=True)
    confidence_score = models.PositiveSmallIntegerField(default=0)
    safety_warnings = models.JSONField(default=list, blank=True)
    missing_questions = models.JSONField(default=list, blank=True)
    form_snapshot = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=1000, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    provider_request_id = models.CharField(max_length=160, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "idempotency_key"),
                name="unique_ai_analysis_idempotency_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["safety_status", "-created_at"]),
        ]
        verbose_name = "Yapay Zekâ Analizi"
        verbose_name_plural = "Yapay Zekâ Analizleri"

    def mark_processing(self):
        self.status = self.Status.PROCESSING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.user} · {str(self.public_id)[:8]} · {self.get_status_display()}"


class AIFieldChange(models.Model):
    class ChangeType(models.TextChoices):
        ACCEPTED = "accepted", "Öneri aynen kabul edildi"
        EDITED = "edited", "Kullanıcı düzenledi"
        CLEARED = "cleared", "Kullanıcı temizledi"
        NOT_APPLIED = "not_applied", "Forma uygulanmadı"

    analysis = models.ForeignKey(
        AIAnalysis,
        related_name="field_changes",
        on_delete=models.CASCADE,
    )
    listing = models.ForeignKey(
        "listings.Listing",
        related_name="ai_field_changes",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    field_name = models.CharField(max_length=80)
    suggested_value = models.JSONField(null=True, blank=True)
    final_value = models.JSONField(null=True, blank=True)
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("field_name",)
        indexes = [models.Index(fields=["analysis", "field_name"])]
        verbose_name = "Yapay Zekâ Alan Değişikliği"
        verbose_name_plural = "Yapay Zekâ Alan Değişiklikleri"

    def __str__(self) -> str:
        return f"{self.analysis} · {self.field_name}"
