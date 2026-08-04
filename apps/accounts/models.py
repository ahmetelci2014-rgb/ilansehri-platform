from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class UserType(models.TextChoices):
        INDIVIDUAL = "individual", "Bireysel"
        BUSINESS = "business", "Kurumsal"
        PROVIDER = "provider", "Hizmet Veren"
        PARTNER = "partner", "Görev Ortağı"

    class VerificationLevel(models.TextChoices):
        BASIC = "basic", "Temel hesap"
        PHONE = "phone", "Telefon doğrulandı"
        IDENTITY = "identity", "Kimlik doğrulandı"
        PROFESSIONAL = "professional", "Profesyonel doğrulandı"

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.INDIVIDUAL,
    )
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=80, blank=True)
    district = models.CharField(max_length=80, blank=True)
    neighborhood = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True)
    bio = models.TextField(max_length=600, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    verification_level = models.CharField(
        max_length=20,
        choices=VerificationLevel.choices,
        default=VerificationLevel.BASIC,
    )
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    completed_transactions = models.PositiveIntegerField(default=0)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    accepts_marketing = models.BooleanField(default=False)

    @property
    def display_name(self) -> str:
        return self.get_full_name().strip() or self.username

    @property
    def trust_score(self) -> int:
        score = 20
        if self.is_email_verified:
            score += 15
        if self.is_phone_verified:
            score += 25
        if self.verification_level in {
            self.VerificationLevel.IDENTITY,
            self.VerificationLevel.PROFESSIONAL,
        }:
            score += 25
        score += min(self.completed_transactions, 10)
        if self.rating_count and self.average_rating >= 4:
            score += 5
        return min(score, 100)

    def __str__(self) -> str:
        return self.display_name


class VerificationCode(models.Model):
    class Channel(models.TextChoices):
        PHONE = "phone", "Telefon"
        EMAIL = "email", "E-posta"

    user = models.ForeignKey(
        User,
        related_name="verification_codes",
        on_delete=models.CASCADE,
    )
    channel = models.CharField(max_length=12, choices=Channel.choices)
    destination = models.CharField(max_length=254)
    code_hash = models.CharField(max_length=256)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "channel", "-created_at"])]

    @classmethod
    def issue(cls, *, user: User, channel: str, destination: str, raw_code: str):
        cls.objects.filter(
            user=user,
            channel=channel,
            consumed_at__isnull=True,
        ).update(consumed_at=timezone.now())
        return cls.objects.create(
            user=user,
            channel=channel,
            destination=destination,
            code_hash=make_password(raw_code),
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    def verify(self, raw_code: str) -> bool:
        if self.consumed_at or self.expires_at <= timezone.now() or self.attempts >= 5:
            return False
        self.attempts += 1
        valid = check_password(raw_code, self.code_hash)
        if valid:
            self.consumed_at = timezone.now()
        self.save(update_fields=["attempts", "consumed_at"])
        return valid


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        User,
        related_name="blocked_users",
        on_delete=models.CASCADE,
    )
    blocked = models.ForeignKey(
        User,
        related_name="blocked_by_users",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("blocker", "blocked"),
                name="unique_user_block",
            )
        ]

    def __str__(self) -> str:
        return f"{self.blocker} → {self.blocked}"


class UserFollow(models.Model):
    follower = models.ForeignKey(
        User,
        related_name="following_links",
        on_delete=models.CASCADE,
    )
    seller = models.ForeignKey(
        User,
        related_name="follower_links",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("follower", "seller"),
                name="unique_user_follow",
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("seller")),
                name="prevent_self_follow",
            ),
        ]
        indexes = [models.Index(fields=["seller", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.follower} → {self.seller}"


class AccountClosureRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "İncelemede"
        CANCELLED = "cancelled", "Kullanıcı iptal etti"
        COMPLETED = "completed", "Tamamlandı"

    user = models.OneToOneField(
        User,
        related_name="closure_request",
        on_delete=models.CASCADE,
    )
    reason = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        related_name="resolved_closure_requests",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-requested_at",)

    def __str__(self) -> str:
        return f"{self.user} · {self.get_status_display()}"
