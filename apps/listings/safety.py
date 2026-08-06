from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal

from apps.accounts.models import AccountRiskEvent
from apps.accounts.trust import record_risk_event

from .message_safety import analyze_message

_PHONE_RE = re.compile(r"(?<!\d)(?:\+?90\s*)?0?5\d{2}[\s.()-]*\d{3}[\s.()-]*\d{2}[\s.()-]*\d{2}(?!\d)")
_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_ADVANCE_RE = re.compile(r"\b(kapora|ön ödeme|on odeme|iban|havale|eft|ödeme linki|odeme linki)\b", re.IGNORECASE)
_URGENCY_RE = re.compile(r"\b(acil|hemen|bugün son|bugun son|son fırsat|son firsat)\b", re.IGNORECASE)


def assess_listing_safety(listing, *, price_guide=None) -> dict:
    score = 0
    flags: list[str] = []

    def add(points: int, label: str):
        nonlocal score
        score += points
        if label not in flags:
            flags.append(label)

    text = f"{listing.title}\n{listing.description}"
    if _PHONE_RE.search(text):
        add(22, "Açıklamada telefon numarası")
    if _URL_RE.search(text):
        add(20, "Harici bağlantı içeriyor")
    if _ADVANCE_RE.search(text):
        add(28, "Kapora veya platform dışı ödeme ifadesi")
    if _URGENCY_RE.search(text) and _ADVANCE_RE.search(text):
        add(18, "Acele ödeme baskısı")
    if len((listing.description or "").strip()) < 40:
        add(10, "Açıklama güvenli değerlendirme için çok kısa")
    if not listing.owner.is_phone_verified and not listing.owner.is_email_verified:
        add(8, "İlan sahibi henüz iletişim doğrulaması yapmadı")

    duplicate_count = 0
    for image in listing.images.all():
        duplicate_count += image.duplicate_owner_count
    if duplicate_count:
        add(35 if duplicate_count >= 2 else 22, "Fotoğraf başka hesaplarda da kullanılmış")

    if price_guide and getattr(price_guide, "available", False) and listing.price:
        median = getattr(price_guide, "median_price", None)
        if median and Decimal(listing.price) < Decimal(median) * Decimal("0.45"):
            add(35, "Fiyat benzer ilanların çok altında")
        elif median and Decimal(listing.price) < Decimal(median) * Decimal("0.65"):
            add(20, "Fiyat benzer ilanların belirgin altında")

    score = min(100, score)
    if score >= 70:
        level, label, tone = "critical", "Kritik inceleme gerekli", "critical"
    elif score >= 45:
        level, label, tone = "high", "Yüksek risk kontrolü", "high"
    elif score >= 20:
        level, label, tone = "medium", "Ek güvenlik kontrolü", "medium"
    else:
        level, label, tone = "low", "Standart güvenlik kontrolü", "safe"
    return {
        "score": score,
        "level": level,
        "label": label,
        "tone": tone,
        "flags": flags,
        "duplicate_image_count": duplicate_count,
        "requires_review": score >= 45,
        "public_advice": "Ürünü görmeden ödeme yapma; şifre, doğrulama kodu veya kart bilgisi paylaşma.",
    }


def record_listing_risks(listing, *, safety_profile: dict | None = None):
    profile = safety_profile or assess_listing_safety(listing)
    if profile["score"] < 20:
        return []
    severity = (
        AccountRiskEvent.Severity.CRITICAL if profile["score"] >= 70 else
        AccountRiskEvent.Severity.HIGH if profile["score"] >= 45 else
        AccountRiskEvent.Severity.MEDIUM
    )
    signal_payload = json.dumps(
        {"score": profile["score"], "flags": sorted(profile["flags"])},
        ensure_ascii=False,
        sort_keys=True,
    )
    signal_digest = hashlib.sha256(signal_payload.encode("utf-8")).hexdigest()[:20]
    events = [record_risk_event(
        subject_user=listing.owner,
        event_type=AccountRiskEvent.EventType.LISTING_CONTENT,
        severity=severity,
        fingerprint=f"listing-content:{listing.pk}:{signal_digest}",
        summary=f"İlan güvenlik kontrolü: {profile['label']}",
        listing=listing,
        details={"score": profile["score"], "flags": profile["flags"]},
    )]
    if profile.get("duplicate_image_count"):
        duplicate_fingerprints = sorted(
            image.fingerprint for image in listing.images.all()
            if image.fingerprint and image.duplicate_owner_count
        )
        duplicate_digest = hashlib.sha256(
            "|".join(duplicate_fingerprints).encode("ascii")
        ).hexdigest()[:20]
        events.append(record_risk_event(
            subject_user=listing.owner,
            event_type=AccountRiskEvent.EventType.DUPLICATE_IMAGE,
            severity=AccountRiskEvent.Severity.HIGH,
            fingerprint=f"duplicate-image:{listing.pk}:{duplicate_digest}",
            summary="İlan fotoğrafı başka hesaplarda da kullanılmış",
            listing=listing,
            details={
                "duplicate_owner_count": profile["duplicate_image_count"],
                "fingerprint_count": len(duplicate_fingerprints),
            },
        ))
    return events


def record_message_risk(message):
    result = analyze_message(message.body)
    if result.level not in {"high", "critical"}:
        return None
    severity = (
        AccountRiskEvent.Severity.CRITICAL
        if result.level == "critical"
        else AccountRiskEvent.Severity.HIGH
    )
    return record_risk_event(
        subject_user=message.sender,
        event_type=AccountRiskEvent.EventType.MESSAGE,
        severity=severity,
        fingerprint=f"message:{message.pk}",
        summary=result.label,
        listing=message.conversation.listing,
        message=message,
        details={"score": result.score, "flags": list(result.flags), "reasons": list(result.reasons)},
    )


def record_listing_report_risk(report):
    severity_map = {
        "fraud": AccountRiskEvent.Severity.HIGH,
        "prohibited": AccountRiskEvent.Severity.HIGH,
        "harassment": AccountRiskEvent.Severity.HIGH,
        "duplicate": AccountRiskEvent.Severity.MEDIUM,
        "wrong_info": AccountRiskEvent.Severity.MEDIUM,
        "other": AccountRiskEvent.Severity.LOW,
    }
    return record_risk_event(
        subject_user=report.listing.owner,
        event_type=AccountRiskEvent.EventType.LISTING_REPORT,
        severity=severity_map.get(report.reason, AccountRiskEvent.Severity.MEDIUM),
        fingerprint=f"listing-report:{report.pk}",
        summary=f"İlan şikâyeti: {report.get_reason_display()}",
        listing=report.listing,
        details={"report_id": report.pk, "reason": report.reason, "details": report.details[:500]},
    )
