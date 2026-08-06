from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from statistics import mean

from django.db.models import Q
from django.utils import timezone

from .models import AccountRiskEvent, UserReport


@dataclass(frozen=True)
class TrustProfile:
    score: int
    tier: str
    tone: str
    account_age_days: int
    account_age_label: str
    completed_transactions: int
    dispute_count: int
    reliability_rate: int | None
    reliability_label: str
    active_report_count: int
    active_risk_count: int
    average_response_minutes: int | None
    response_label: str
    badges: tuple[str, ...]
    public_note: str


def _account_age_label(days: int) -> str:
    if days >= 730:
        return f"{days // 365} yıldan uzun süredir üye"
    if days >= 365:
        return "1 yıldan uzun süredir üye"
    if days >= 60:
        return f"{days // 30} aydır üye"
    return f"{max(days, 1)} gündür üye"


def _response_minutes(user) -> int | None:
    from apps.listings.models import Conversation

    samples: list[float] = []
    conversations = (
        Conversation.objects.filter(seller=user)
        .prefetch_related("messages")
        .order_by("-updated_at")[:50]
    )
    for conversation in conversations:
        ordered = list(conversation.messages.all())
        first_incoming = next((item for item in ordered if item.sender_id != user.pk), None)
        if not first_incoming:
            continue
        first_reply = next(
            (item for item in ordered if item.sender_id == user.pk and item.created_at > first_incoming.created_at),
            None,
        )
        if first_reply:
            samples.append((first_reply.created_at - first_incoming.created_at).total_seconds() / 60)
    return round(mean(samples)) if samples else None


def _response_label(minutes: int | None) -> str:
    if minutes is None:
        return "Henüz yeterli yanıt verisi yok"
    if minutes < 60:
        return f"Ortalama {max(minutes, 1)} dakikada yanıt"
    if minutes < 1440:
        return f"Ortalama {max(1, round(minutes / 60))} saatte yanıt"
    return f"Ortalama {max(1, round(minutes / 1440))} günde yanıt"


def build_trust_profile(
    user, *, include_private: bool = False, include_response: bool = True
) -> TrustProfile:
    from apps.listings.models import Transaction, TransactionEvent

    completed = Transaction.objects.filter(
        Q(buyer=user) | Q(seller=user), status=Transaction.Status.COMPLETED
    ).count()
    disputes = (
        TransactionEvent.objects.filter(
            Q(transaction__buyer=user) | Q(transaction__seller=user),
            event_type=TransactionEvent.Type.DISPUTED,
        )
        .values("transaction_id")
        .distinct()
        .count()
    )
    active_report_count = UserReport.objects.filter(
        reported_user=user, status__in=[UserReport.Status.OPEN, UserReport.Status.REVIEWING]
    ).count()
    active_risk_count = AccountRiskEvent.objects.filter(
        subject_user=user, status__in=[AccountRiskEvent.Status.OPEN, AccountRiskEvent.Status.REVIEWING]
    ).count()
    listing_report_count = user.listings.filter(
        reports__status__in=["open", "reviewing"]
    ).distinct().count()
    active_report_count += listing_report_count

    score = user.trust_score
    if user.rating_count >= 3 and user.average_rating >= 4:
        score += 5
    if disputes:
        score -= min(20, disputes * 5)
    if include_private:
        score -= min(24, active_report_count * 6)
        score -= min(30, active_risk_count * 5)
    score = max(0, min(100, score))

    if score >= 85:
        tier, tone = "Çok güçlü güven profili", "excellent"
    elif score >= 70:
        tier, tone = "Güçlü güven profili", "strong"
    elif score >= 50:
        tier, tone = "Gelişen güven profili", "developing"
    else:
        tier, tone = "Yeni / temel güven profili", "basic"

    response_minutes = _response_minutes(user) if include_response else None
    reliability_rate = (
        round((completed / (completed + disputes)) * 100)
        if completed + disputes
        else None
    )
    reliability_label = (
        f"%{reliability_rate} sorunsuz işlem"
        if reliability_rate is not None
        else "Henüz yeterli işlem verisi yok"
    )
    badges: list[str] = []
    if user.is_phone_verified:
        badges.append("Telefon doğrulandı")
    if user.is_email_verified:
        badges.append("E-posta doğrulandı")
    if user.verification_level in {user.VerificationLevel.IDENTITY, user.VerificationLevel.PROFESSIONAL}:
        badges.append(user.get_verification_level_display())
    if completed >= 3:
        badges.append("Başarılı işlem geçmişi")
    if user.rating_count >= 3 and user.average_rating >= 4:
        badges.append("Yüksek kullanıcı puanı")
    if user.account_age_days >= 365:
        badges.append("Uzun süredir üye")

    public_note = "Güven puanı doğrulama, işlem ve kullanıcı değerlendirmesi sinyallerinden oluşur."
    if include_private:
        public_note = f"Açık şikâyet: {active_report_count} · Açık risk kaydı: {active_risk_count}"

    return TrustProfile(
        score=score,
        tier=tier,
        tone=tone,
        account_age_days=user.account_age_days,
        account_age_label=_account_age_label(user.account_age_days),
        completed_transactions=completed,
        dispute_count=disputes,
        reliability_rate=reliability_rate,
        reliability_label=reliability_label,
        active_report_count=active_report_count,
        active_risk_count=active_risk_count,
        average_response_minutes=response_minutes,
        response_label=(
            _response_label(response_minutes)
            if include_response
            else "Yanıt bilgisi kullanıcı profilinde hesaplanır"
        ),
        badges=tuple(badges),
        public_note=public_note,
    )


def record_risk_event(
    *, subject_user, event_type: str, severity: str, fingerprint: str, summary: str,
    listing=None, message=None, user_report=None, details: dict | None = None,
):
    event, created = AccountRiskEvent.objects.get_or_create(
        fingerprint=fingerprint[:96],
        defaults={
            "subject_user": subject_user,
            "event_type": event_type,
            "severity": severity,
            "summary": summary[:240],
            "source_listing": listing,
            "source_message": message,
            "source_user_report": user_report,
            "details": details or {},
        },
    )
    if not created and event.status == AccountRiskEvent.Status.DISMISSED:
        return event
    return event
