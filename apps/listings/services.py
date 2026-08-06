from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import re
import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.core.files.base import ContentFile
from django.db import transaction as db_transaction
from django.db.models import Avg, Count, F, Q
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import (
    Appointment,
    Conversation,
    Favorite,
    Listing,
    ListingPriceHistory,
    Notification,
    Offer,
    OfferEvent,
    Review,
    SavedSearch,
    SavedSearchMatch,
    Transaction,
    TransactionEvent,
)


_PHONE_PATTERN = re.compile(r"(?:\+?90|0)?\s*5\d{2}[\s.-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}")
_REPEATED_PUNCTUATION = re.compile(r"([!?.,])\1{2,}")


def assess_listing_quality(listing: Listing) -> dict:
    """Return a deterministic quality and moderation summary without storing extra data."""
    checks = []

    def add(label, points, passed, suggestion=""):
        checks.append(
            {
                "label": label,
                "points": points if passed else 0,
                "max_points": points,
                "passed": bool(passed),
                "suggestion": suggestion,
            }
        )

    title = (listing.title or "").strip()
    description = (listing.description or "").strip()
    images = list(listing.images.all())
    add("Açıklayıcı başlık", 12, len(title) >= 18, "Başlığı en az 18 karakter ve daha açıklayıcı yap.")
    add("Ayrıntılı açıklama", 20, len(description) >= 120, "Kusur, teslim ve kullanım ayrıntılarını ekle.")
    add("Yeterli fotoğraf", 20, len(images) >= 4, "En az 4 farklı açıdan fotoğraf ekle.")
    add("Fiyat bilgisi", 10, bool(listing.price_on_request or listing.price), "Fiyat veya teklif seçeneği belirt.")
    add("Konum ayrıntısı", 10, bool(listing.city and listing.district), "Şehir ve ilçe bilgisini tamamla.")
    add("Teslim / durum bilgisi", 8, bool(listing.delivery_type or listing.condition), "Teslim ve ürün durumunu belirt.")

    category_complete = False
    if listing.kind == Listing.Kind.VEHICLE:
        category_complete = bool(listing.brand and listing.model_name and listing.model_year and listing.mileage is not None)
    elif listing.kind == Listing.Kind.REAL_ESTATE:
        category_complete = bool(listing.room_count and listing.area_m2)
    elif listing.kind == Listing.Kind.SERVICE:
        category_complete = bool(listing.service_area and listing.fee_type)
    elif listing.kind == Listing.Kind.JOB:
        category_complete = bool(listing.job_type)
    else:
        category_complete = bool(listing.brand or listing.condition or listing.delivery_type)
    add("Kategori ayrıntıları", 12, category_complete, "Kategoriye özel alanları doldur.")
    add("Doğrulanmış satıcı", 8, bool(getattr(listing.owner, "is_phone_verified", False)), "Telefon doğrulamasını tamamla.")

    score = min(100, sum(item["points"] for item in checks))
    if score >= 85:
        level, tone = "Çok güçlü", "excellent"
    elif score >= 70:
        level, tone = "Güçlü", "good"
    elif score >= 50:
        level, tone = "Geliştirilebilir", "medium"
    else:
        level, tone = "Zayıf", "weak"

    risk_flags = []
    if title and title == title.upper() and any(char.isalpha() for char in title):
        risk_flags.append("Başlığın tamamı büyük harf")
    if _REPEATED_PUNCTUATION.search(title + " " + description):
        risk_flags.append("Aşırı noktalama işareti")
    if _PHONE_PATTERN.search(description):
        risk_flags.append("Açıklamada telefon numarası")
    if len(description) < 40:
        risk_flags.append("Çok kısa açıklama")
    if not images:
        risk_flags.append("Fotoğraf yok")

    return {
        "score": score,
        "level": level,
        "tone": tone,
        "checks": checks,
        "suggestions": [item["suggestion"] for item in checks if not item["passed"] and item["suggestion"]],
        "risk_flags": risk_flags,
        "passed_count": sum(1 for item in checks if item["passed"]),
        "total_count": len(checks),
    }


def optimize_listing_image(uploaded_file, *, max_edge=1800, quality=84):
    """Resize and normalize listing photos while safely falling back to the original upload."""
    try:
        uploaded_file.seek(0)
        source = Image.open(uploaded_file)
        if getattr(source, "is_animated", False):
            uploaded_file.seek(0)
            return uploaded_file
        image = ImageOps.exif_transpose(source)
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        has_alpha = image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info)
        buffer = BytesIO()
        original_stem = Path(getattr(uploaded_file, "name", "ilan-fotografi")).stem[:80] or "ilan-fotografi"
        if has_alpha:
            image.save(buffer, format="PNG", optimize=True)
            filename = f"{original_stem}.png"
        else:
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
            filename = f"{original_stem}.jpg"
        return ContentFile(buffer.getvalue(), name=filename)
    except (OSError, ValueError, UnidentifiedImageError):
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass
        return uploaded_file


def consume_rate_limit(request, action: str, *, limit=10, period=600) -> bool:
    """Simple cache-backed anti-spam guard for write-heavy marketplace actions."""
    if getattr(settings, "IS_TESTING", False):
        return True
    if request.user.is_authenticated:
        identity = f"u{request.user.pk}"
    else:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        identity = forwarded or request.META.get("REMOTE_ADDR", "anonymous")
    window = int(time.time() // period)
    key = f"ilansehri:rate:{action}:{identity}:{window}"
    if cache.add(key, 1, timeout=period + 10):
        return True
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=period + 10)
        count = 1
    return count <= limit


def _notification_preferences(user):
    from apps.accounts.models import NotificationPreference

    preference, _ = NotificationPreference.objects.get_or_create(user=user)
    return preference


def _notification_absolute_link(link: str) -> str:
    link = (link or "").strip()
    if not link:
        return settings.PUBLIC_BASE_URL or ""
    if link.startswith(("http://", "https://")):
        return link
    if settings.PUBLIC_BASE_URL:
        return f"{settings.PUBLIC_BASE_URL}{link if link.startswith('/') else '/' + link}"
    return link


def _send_notification_email(*, user, title, body, link):
    if not user.email or not user.is_email_verified:
        return 0
    lines = [title]
    if body:
        lines.extend(["", body])
    absolute_link = _notification_absolute_link(link)
    if absolute_link:
        lines.extend(["", f"Ayrıntılar: {absolute_link}"])
    lines.extend(["", "Bu e-posta İlan Şehri bildirim tercihlerine göre gönderildi."])
    return send_mail(
        subject=f"İlan Şehri · {title}",
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def create_notification(
    *,
    user,
    notification_type,
    title,
    body="",
    link="",
    actor=None,
    listing=None,
):
    if actor and actor.pk == user.pk:
        actor = None
    preference = _notification_preferences(user)
    notification = None
    if preference.allows_in_app(notification_type):
        notification = Notification.objects.create(
            user=user,
            actor=actor,
            listing=listing,
            notification_type=notification_type,
            title=title,
            body=body[:320],
            link=link[:320],
        )
    if preference.allows_email(notification_type) and user.email and user.is_email_verified:
        db_transaction.on_commit(
            lambda: _send_notification_email(
                user=user,
                title=title,
                body=body[:320],
                link=link[:320],
            )
        )
    return notification


def create_offer_event(*, offer, actor, event_type, amount=None, message=""):
    return OfferEvent.objects.create(
        offer=offer,
        actor=actor,
        event_type=event_type,
        amount=amount,
        message=(message or "")[:1200],
    )


def _appointment_conflicts(*, proposer, invitee, starts_at, duration_minutes, exclude_pk=None) -> bool:
    """Return True when either participant already has an overlapping active appointment."""
    end_at = starts_at + timedelta(minutes=duration_minutes)
    window_start = starts_at - timedelta(hours=4)
    window_end = end_at + timedelta(hours=4)
    candidates = Appointment.objects.filter(
        status__in=[Appointment.Status.PENDING, Appointment.Status.ACCEPTED],
        starts_at__gte=window_start,
        starts_at__lte=window_end,
    ).filter(
        Q(proposer__in=[proposer, invitee]) | Q(invitee__in=[proposer, invitee])
    )
    if exclude_pk:
        candidates = candidates.exclude(pk=exclude_pk)
    for item in candidates.only("starts_at", "duration_minutes"):
        item_end = item.starts_at + timedelta(minutes=item.duration_minutes)
        if item.starts_at < end_at and item_end > starts_at:
            return True
    return False


@db_transaction.atomic
def create_appointment(*, conversation: Conversation, proposer, cleaned_data: dict) -> Appointment:
    locked_conversation = (
        Conversation.objects.select_for_update()
        .select_related("listing", "buyer", "seller")
        .get(pk=conversation.pk)
    )
    if proposer.pk not in {locked_conversation.buyer_id, locked_conversation.seller_id}:
        raise PermissionError("Bu görüşme için randevu oluşturamazsın.")
    invitee = locked_conversation.other_participant(proposer)
    starts_at = cleaned_data["starts_at"]
    duration_minutes = cleaned_data["duration_minutes"]
    if _appointment_conflicts(
        proposer=proposer,
        invitee=invitee,
        starts_at=starts_at,
        duration_minutes=duration_minutes,
    ):
        raise ValueError("Bu saat aralığında taraflardan birinin başka bir randevusu bulunuyor.")

    appointment = Appointment.objects.create(
        conversation=locked_conversation,
        listing=locked_conversation.listing,
        proposer=proposer,
        invitee=invitee,
        appointment_type=cleaned_data["appointment_type"],
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        city=cleaned_data.get("city", ""),
        district=cleaned_data.get("district", ""),
        place=cleaned_data.get("place", ""),
        note=cleaned_data.get("note", ""),
    )
    create_notification(
        user=invitee,
        actor=proposer,
        listing=locked_conversation.listing,
        notification_type=Notification.Type.TRANSACTION,
        title="Yeni randevu önerisi",
        body=(
            f"{proposer.display_name}, {starts_at:%d.%m.%Y %H:%M} için "
            f"{appointment.get_appointment_type_display().lower()} önerdi."
        ),
        link=appointment.get_absolute_url(),
    )
    return appointment


@db_transaction.atomic
def respond_appointment(*, appointment: Appointment, actor, action: str) -> Appointment:
    locked = (
        Appointment.objects.select_for_update()
        .select_related("listing", "proposer", "invitee")
        .get(pk=appointment.pk)
    )
    if not locked.is_participant(actor):
        raise PermissionError("Bu randevuya erişemezsin.")
    now = timezone.now()

    if action in {"accept", "decline"}:
        if actor.pk != locked.invitee_id:
            raise PermissionError("Randevuya yalnız davet edilen kullanıcı yanıt verebilir.")
        if locked.status != Appointment.Status.PENDING:
            raise ValueError("Bu randevu önerisi artık yanıt beklemiyor.")
        if locked.starts_at <= now:
            raise ValueError("Geçmiş tarihli randevu onaylanamaz.")
        if action == "accept" and _appointment_conflicts(
            proposer=locked.proposer,
            invitee=locked.invitee,
            starts_at=locked.starts_at,
            duration_minutes=locked.duration_minutes,
            exclude_pk=locked.pk,
        ):
            raise ValueError("Bu saat aralığında taraflardan birinin başka bir randevusu bulunuyor.")
        locked.status = (
            Appointment.Status.ACCEPTED if action == "accept" else Appointment.Status.DECLINED
        )
        locked.responded_at = now
        locked.save(update_fields=["status", "responded_at", "updated_at"])
        recipient = locked.proposer
        title = "Randevu onaylandı" if action == "accept" else "Randevu reddedildi"
        body = (
            f"{actor.display_name}, {locked.starts_at:%d.%m.%Y %H:%M} tarihli randevu önerisine "
            f"{'onay verdi' if action == 'accept' else 'olumsuz yanıt verdi'}."
        )
    elif action == "cancel":
        if locked.status not in {Appointment.Status.PENDING, Appointment.Status.ACCEPTED}:
            raise ValueError("Bu randevu iptal edilemez.")
        if locked.starts_at <= now:
            raise ValueError("Başlangıç zamanı geçen randevu iptal edilemez.")
        locked.status = Appointment.Status.CANCELLED
        locked.responded_at = now
        locked.save(update_fields=["status", "responded_at", "updated_at"])
        recipient = locked.other_participant(actor)
        title = "Randevu iptal edildi"
        body = f"{actor.display_name}, {locked.starts_at:%d.%m.%Y %H:%M} tarihli randevuyu iptal etti."
    else:
        raise ValueError("Geçersiz randevu işlemi.")

    create_notification(
        user=recipient,
        actor=actor,
        listing=locked.listing,
        notification_type=Notification.Type.TRANSACTION,
        title=title,
        body=body,
        link=locked.get_absolute_url(),
    )
    return locked


@db_transaction.atomic
def send_appointment_reminders(*, now=None) -> int:
    """Send a single reminder for accepted appointments within the next 24 hours."""
    now = now or timezone.now()
    lower = now
    upper = now + timedelta(hours=24)
    queryset = (
        Appointment.objects.select_for_update()
        .filter(
            status=Appointment.Status.ACCEPTED,
            reminder_sent_at__isnull=True,
            starts_at__gte=lower,
            starts_at__lte=upper,
        )
        .select_related("listing", "proposer", "invitee")
    )
    sent = 0
    for appointment in queryset:
        for recipient in (appointment.proposer, appointment.invitee):
            other = appointment.other_participant(recipient)
            create_notification(
                user=recipient,
                actor=other,
                listing=appointment.listing,
                notification_type=Notification.Type.TRANSACTION,
                title="Yaklaşan randevun",
                body=(
                    f"{appointment.listing.title}: {appointment.starts_at:%d.%m.%Y %H:%M} · "
                    f"{appointment.get_appointment_type_display()}"
                ),
                link=appointment.get_absolute_url(),
            )
        appointment.reminder_sent_at = now
        appointment.save(update_fields=["reminder_sent_at", "updated_at"])
        sent += 1
    return sent


def notify_followers_new_listing(listing: Listing) -> int:
    if listing.status != Listing.Status.PUBLISHED:
        return 0
    from apps.accounts.models import User, UserFollow

    follower_ids = UserFollow.objects.filter(seller=listing.owner).values_list("follower_id", flat=True)
    recipients = User.objects.filter(pk__in=follower_ids, is_active=True).exclude(pk=listing.owner_id)
    created = 0
    for recipient in recipients.iterator():
        if Notification.objects.filter(
            user=recipient,
            listing=listing,
            notification_type=Notification.Type.FOLLOW,
        ).exists():
            continue
        notification = create_notification(
            user=recipient,
            actor=listing.owner,
            listing=listing,
            notification_type=Notification.Type.FOLLOW,
            title=f"{listing.owner.display_name} yeni ilan yayınladı",
            body=listing.title,
            link=listing.get_absolute_url(),
        )
        if notification is not None:
            created += 1
    return created



def notify_saved_searches_new_listing(listing: Listing) -> int:
    """Yeni yayınlanan ilan için anlık kayıtlı arama bildirimlerini üret."""
    if listing.status != Listing.Status.PUBLISHED:
        return 0
    from .search_alerts import listing_matches_saved_search

    created_count = 0
    searches = (
        SavedSearch.objects.filter(
            alert_enabled=True,
            alert_frequency=SavedSearch.AlertFrequency.INSTANT,
            user__is_active=True,
        )
        .exclude(user_id=listing.owner_id)
        .select_related("user")
    )
    for saved in searches.iterator():
        if SavedSearchMatch.objects.filter(saved_search=saved, listing=listing).exists():
            continue
        if not listing_matches_saved_search(saved, listing):
            continue
        match, was_created = SavedSearchMatch.objects.get_or_create(
            saved_search=saved,
            listing=listing,
        )
        if not was_created:
            continue
        notification = create_notification(
            user=saved.user,
            actor=listing.owner,
            listing=listing,
            notification_type=Notification.Type.SEARCH_ALERT,
            title=f"{saved.name} aramana uygun yeni ilan",
            body=listing.title[:320],
            link=listing.get_absolute_url(),
        )
        if notification is not None:
            notified_at = timezone.now()
            match.notified_at = notified_at
            match.save(update_fields=["notified_at"])
            saved.last_notified_at = notified_at
            saved.save(update_fields=["last_notified_at", "updated_at"])
            created_count += 1
    return created_count

def notify_listing_publication(listing: Listing) -> dict:
    """Run every non-blocking publication notification and matching hook once."""
    follower_count = notify_followers_new_listing(listing)
    saved_search_count = notify_saved_searches_new_listing(listing)
    from .matching import sync_listing_matches

    match_result = sync_listing_matches(listing, notify=True)
    return {
        "followers": follower_count,
        "saved_search_alerts": saved_search_count,
        "matches_created": match_result["created"],
        "matches_updated": match_result["updated"],
    }


@db_transaction.atomic
def notify_price_drop_favorites(history: ListingPriceHistory) -> int:
    locked_history = (
        ListingPriceHistory.objects.select_for_update()
        .select_related("listing", "listing__owner")
        .get(pk=history.pk)
    )
    if (
        not locked_history.is_drop
        or locked_history.notifications_sent_at is not None
        or locked_history.listing.status != Listing.Status.PUBLISHED
    ):
        return 0
    recipient_ids = (
        Favorite.objects.filter(listing=locked_history.listing)
        .exclude(user_id=locked_history.listing.owner_id)
        .values_list("user_id", flat=True)
        .distinct()
    )
    from apps.accounts.models import User

    created = 0
    for recipient in User.objects.filter(pk__in=recipient_ids, is_active=True).iterator():
        notification = create_notification(
            user=recipient,
            actor=locked_history.listing.owner,
            listing=locked_history.listing,
            notification_type=Notification.Type.PRICE_DROP,
            title="Favorindeki ilanın fiyatı düştü",
            body=(
                f"{locked_history.listing.title}: {locked_history.old_price:,.0f} TL → "
                f"{locked_history.new_price:,.0f} TL"
            ).replace(",", "."),
            link=locked_history.listing.get_absolute_url(),
        )
        if notification is not None:
            created += 1
    locked_history.notifications_sent_at = timezone.now()
    locked_history.save(update_fields=["notifications_sent_at"])
    history.notifications_sent_at = locked_history.notifications_sent_at
    return created


def record_price_change(*, listing: Listing, old_price, new_price, actor=None):
    if old_price is None or new_price is None or old_price == new_price:
        return None
    history = ListingPriceHistory.objects.create(
        listing=listing,
        old_price=old_price,
        new_price=new_price,
        changed_by=actor,
    )
    notify_price_drop_favorites(history)
    return history


@db_transaction.atomic
def counter_offer(*, offer: Offer, actor, amount, message: str) -> Offer:
    locked_offer = (
        Offer.objects.select_for_update()
        .select_related("listing", "listing__owner", "sender", "last_actor")
        .get(pk=offer.pk)
    )
    if not locked_offer.can_respond(actor):
        raise PermissionError("Bu teklif sırası sende değil.")
    if locked_offer.status != Offer.Status.PENDING:
        raise ValueError("Teklif artık beklemede değil.")
    if amount is None or amount <= 0:
        raise ValueError("Geçerli bir teklif tutarı gir.")

    locked_offer.amount = amount
    locked_offer.message = message
    locked_offer.last_actor = actor
    locked_offer.counter_count += 1
    locked_offer.responded_at = None
    locked_offer.save(
        update_fields=[
            "amount",
            "message",
            "last_actor",
            "counter_count",
            "responded_at",
            "updated_at",
        ]
    )
    create_offer_event(
        offer=locked_offer,
        actor=actor,
        event_type=OfferEvent.Type.COUNTERED,
        amount=amount,
        message=message,
    )
    recipient = locked_offer.other_participant(actor)
    create_notification(
        user=recipient,
        actor=actor,
        listing=locked_offer.listing,
        notification_type=Notification.Type.OFFER,
        title="Yeni karşı teklif geldi",
        body=f"{actor.display_name} {amount:,.0f} TL karşı teklif gönderdi.".replace(",", "."),
        link=f"{reverse('listings:offer_center')}?focus={locked_offer.pk}",
    )
    return locked_offer


@db_transaction.atomic
def accept_offer(*, offer: Offer, actor) -> Transaction:
    locked_offer = (
        Offer.objects.select_for_update()
        .select_related("listing", "listing__owner", "sender", "last_actor")
        .get(pk=offer.pk)
    )
    listing = Listing.objects.select_for_update().get(pk=locked_offer.listing_id)
    if not locked_offer.can_respond(actor):
        raise PermissionError("Bu teklifi kabul etme sırası sende değil.")
    if locked_offer.status != Offer.Status.PENDING:
        raise ValueError("Teklif artık beklemede değil.")
    if listing.status not in {Listing.Status.PUBLISHED, Listing.Status.PAUSED}:
        raise ValueError("Bu ilan için işlem başlatılamaz.")
    if locked_offer.sender_id == listing.owner_id:
        raise ValueError("Kullanıcı kendi ilanıyla işlem oluşturamaz.")

    locked_offer.status = Offer.Status.ACCEPTED
    locked_offer.responded_at = timezone.now()
    locked_offer.save(update_fields=["status", "responded_at", "updated_at"])
    create_offer_event(
        offer=locked_offer,
        actor=actor,
        event_type=OfferEvent.Type.ACCEPTED,
        amount=locked_offer.amount,
        message="Teklif kabul edildi.",
    )
    Offer.objects.filter(listing=listing, status=Offer.Status.PENDING).exclude(
        pk=locked_offer.pk
    ).update(status=Offer.Status.REJECTED, responded_at=timezone.now())

    amount = locked_offer.amount if locked_offer.amount is not None else listing.price
    transaction, _ = Transaction.objects.get_or_create(
        offer=locked_offer,
        defaults={
            "listing": listing,
            "buyer": locked_offer.sender,
            "seller": listing.owner,
            "amount": amount,
            "delivery_type": listing.delivery_type,
        },
    )
    if not transaction.events.exists():
        record_transaction_event(
            transaction=transaction,
            actor=actor,
            event_type=TransactionEvent.Type.CREATED,
            note="Teklif kabul edildi ve güvenli işlem kaydı açıldı.",
        )
    listing.status = Listing.Status.PAUSED
    listing.save(update_fields=["status", "updated_at"])

    recipient = locked_offer.other_participant(actor)
    create_notification(
        user=recipient,
        actor=actor,
        listing=listing,
        notification_type=Notification.Type.TRANSACTION,
        title="Teklif kabul edildi",
        body="Anlaşma sağlandı. Teslim ve işlem adımlarını güvenli işlem ekranından takip et.",
        link=transaction.get_absolute_url(),
    )
    return transaction


HANDOVER_CODE_TTL = timedelta(minutes=15)
HANDOVER_CODE_COOLDOWN = timedelta(seconds=60)
HANDOVER_CODE_MAX_ATTEMPTS = 5
REVIEW_BLIND_PERIOD = timedelta(days=7)
REVIEW_WINDOW = timedelta(days=30)


def record_transaction_event(
    *, transaction: Transaction, event_type: str, actor=None, note: str = "", metadata: dict | None = None
) -> TransactionEvent:
    return TransactionEvent.objects.create(
        transaction=transaction,
        actor=actor,
        event_type=event_type,
        note=(note or "")[:240],
        metadata=metadata or {},
    )


@db_transaction.atomic
def start_transaction_delivery(*, transaction: Transaction, actor) -> Transaction:
    locked = Transaction.objects.select_for_update().select_related("listing", "buyer", "seller").get(
        pk=transaction.pk
    )
    if actor.pk != locked.seller_id:
        raise PermissionError("Teslim aşamasını yalnız satıcı başlatabilir.")
    if locked.status != Transaction.Status.AGREED:
        raise ValueError("Bu işlem teslim aşamasına geçirilemez.")
    now = timezone.now()
    locked.status = Transaction.Status.DELIVERY
    locked.delivery_type = locked.delivery_type or locked.listing.delivery_type
    locked.delivery_started_at = now
    locked.save(update_fields=["status", "delivery_type", "delivery_started_at", "updated_at"])
    record_transaction_event(
        transaction=locked, actor=actor, event_type=TransactionEvent.Type.DELIVERY_STARTED,
        note=f"Teslim yöntemi: {locked.get_delivery_type_display() or 'Görüşülür'}",
    )
    create_notification(
        user=locked.buyer, actor=actor, listing=locked.listing,
        notification_type=Notification.Type.TRANSACTION,
        title="Teslim aşaması başladı",
        body="Satıcı işlemi teslim / hizmet aşamasına geçirdi.",
        link=locked.get_absolute_url(),
    )
    return locked


@db_transaction.atomic
def issue_handover_code(*, transaction: Transaction, actor) -> tuple[Transaction, str]:
    locked = Transaction.objects.select_for_update().select_related("listing", "buyer", "seller").get(
        pk=transaction.pk
    )
    if actor.pk != locked.buyer_id:
        raise PermissionError("Teslim kodunu yalnız alıcı oluşturabilir.")
    if locked.status != Transaction.Status.DELIVERY or not locked.requires_handover_code:
        raise ValueError("Bu işlem için teslim kodu kullanılamaz.")
    if locked.handover_verified_at:
        raise ValueError("Teslim kodu daha önce doğrulandı.")
    now = timezone.now()
    if locked.handover_code_created_at and locked.handover_code_created_at > now - HANDOVER_CODE_COOLDOWN:
        raise ValueError("Yeni teslim kodu oluşturmadan önce 60 saniye bekle.")
    raw_code = f"{secrets.randbelow(1_000_000):06d}"
    locked.handover_code_hash = make_password(raw_code)
    locked.handover_code_created_at = now
    locked.handover_code_attempts = 0
    locked.save(
        update_fields=["handover_code_hash", "handover_code_created_at", "handover_code_attempts", "updated_at"]
    )
    record_transaction_event(
        transaction=locked, actor=actor, event_type=TransactionEvent.Type.CODE_CREATED,
        note="15 dakika geçerli teslim kodu oluşturuldu.",
    )
    create_notification(
        user=locked.seller, actor=actor, listing=locked.listing,
        notification_type=Notification.Type.TRANSACTION,
        title="Alıcı teslim kodu oluşturdu",
        body="Kodu yalnız yüz yüze teslim anında alıcıdan iste ve güvenli işlem ekranına gir.",
        link=locked.get_absolute_url(),
    )
    return locked, raw_code


@db_transaction.atomic
def verify_handover_code(*, transaction: Transaction, actor, raw_code: str) -> Transaction:
    locked = Transaction.objects.select_for_update().select_related("listing", "buyer", "seller").get(
        pk=transaction.pk
    )
    if actor.pk != locked.seller_id:
        raise PermissionError("Teslim kodunu yalnız satıcı doğrulayabilir.")
    if locked.status != Transaction.Status.DELIVERY or not locked.requires_handover_code:
        raise ValueError("Bu işlem için teslim kodu doğrulanamaz.")
    if locked.handover_verified_at:
        return locked
    now = timezone.now()
    if not locked.handover_code_hash or not locked.handover_code_created_at:
        raise ValueError("Alıcının önce teslim kodu oluşturması gerekiyor.")
    if locked.handover_code_created_at < now - HANDOVER_CODE_TTL:
        locked.handover_code_hash = ""
        locked.save(update_fields=["handover_code_hash", "updated_at"])
        raise ValueError("Teslim kodunun süresi doldu. Alıcı yeni kod oluşturmalı.")
    if locked.handover_code_attempts >= HANDOVER_CODE_MAX_ATTEMPTS:
        raise ValueError("Çok fazla hatalı deneme yapıldı. Alıcı yeni kod oluşturmalı.")
    locked.handover_code_attempts += 1
    if not check_password(raw_code, locked.handover_code_hash):
        locked.save(update_fields=["handover_code_attempts", "updated_at"])
        raise ValueError("Teslim kodu hatalı.")
    locked.handover_verified_at = now
    locked.seller_confirmed = True
    locked.seller_confirmed_at = now
    locked.handover_code_hash = ""
    locked.save(
        update_fields=[
            "handover_code_attempts", "handover_verified_at", "seller_confirmed",
            "seller_confirmed_at", "handover_code_hash", "updated_at",
        ]
    )
    record_transaction_event(
        transaction=locked, actor=actor, event_type=TransactionEvent.Type.HANDOVER_VERIFIED,
        note="Tek kullanımlık teslim kodu doğrulandı.",
    )
    record_transaction_event(
        transaction=locked, actor=actor, event_type=TransactionEvent.Type.SELLER_CONFIRMED,
        note="Satıcı teslimi kod ile onayladı.",
    )
    create_notification(
        user=locked.buyer, actor=actor, listing=locked.listing,
        notification_type=Notification.Type.TRANSACTION,
        title="Teslim kodu doğrulandı",
        body="Satıcı teslim kodunu doğruladı. Ürünü veya hizmeti kontrol ettikten sonra tamamlamayı onayla.",
        link=locked.get_absolute_url(),
    )
    return locked


@db_transaction.atomic
def confirm_transaction(*, transaction: Transaction, actor) -> Transaction:
    locked = Transaction.objects.select_for_update().select_related("listing", "buyer", "seller").get(
        pk=transaction.pk
    )
    if not locked.is_participant(actor):
        raise PermissionError("Bu işlemin tarafı değilsin.")
    if locked.status != Transaction.Status.DELIVERY:
        raise ValueError("Tamamlama onayı yalnız teslim aşamasında verilebilir.")
    now = timezone.now()
    if actor.pk == locked.buyer_id:
        if locked.requires_handover_code and not locked.handover_verified_at:
            raise ValueError("Önce satıcının teslim kodunu doğrulaması gerekiyor.")
        if not locked.buyer_confirmed:
            locked.buyer_confirmed = True
            locked.buyer_confirmed_at = now
            locked.save(update_fields=["buyer_confirmed", "buyer_confirmed_at", "updated_at"])
            record_transaction_event(
                transaction=locked, actor=actor, event_type=TransactionEvent.Type.BUYER_CONFIRMED,
                note="Alıcı teslimi / hizmeti onayladı.",
            )
    else:
        if locked.requires_handover_code and not locked.handover_verified_at:
            raise ValueError("Elden veya yerinde teslimde satıcı onayı teslim kodu ile verilir.")
        if not locked.seller_confirmed:
            locked.seller_confirmed = True
            locked.seller_confirmed_at = now
            locked.save(update_fields=["seller_confirmed", "seller_confirmed_at", "updated_at"])
            record_transaction_event(
                transaction=locked, actor=actor, event_type=TransactionEvent.Type.SELLER_CONFIRMED,
                note="Satıcı teslimi / hizmeti onayladı.",
            )
    finalize_transaction(locked)
    return Transaction.objects.get(pk=locked.pk)


def review_window_is_open(transaction: Transaction, *, now=None) -> bool:
    now = now or timezone.now()
    completed_reference = transaction.completed_at or transaction.updated_at or transaction.created_at
    return bool(
        transaction.status == Transaction.Status.COMPLETED
        and completed_reference
        and completed_reference >= now - REVIEW_WINDOW
    )


def publish_due_reviews(*, now=None) -> int:
    now = now or timezone.now()
    due = list(
        Review.objects.filter(is_visible=False, created_at__lte=now - REVIEW_BLIND_PERIOD)
        .select_related("reviewed_user", "reviewer", "transaction__listing")
    )
    if not due:
        return 0
    Review.objects.filter(pk__in=[item.pk for item in due]).update(is_visible=True, published_at=now)
    reviewed_users = {item.reviewed_user_id: item.reviewed_user for item in due}
    for user in reviewed_users.values():
        refresh_user_rating(user)
    for item in due:
        create_notification(
            user=item.reviewed_user, actor=item.reviewer, listing=item.transaction.listing,
            notification_type=Notification.Type.REVIEW,
            title="İşlem değerlendirmen yayınlandı",
            body=f"Tamamlanan işlem için {item.rating}/5 puanlık değerlendirme yayınlandı.",
            link=reverse("accounts:public_profile", kwargs={"username": item.reviewed_user.username}),
        )
    return len(due)


def reject_offer(*, offer: Offer, actor) -> None:
    if not offer.can_respond(actor):
        raise PermissionError("Bu teklifi reddetme sırası sende değil.")
    if offer.status != Offer.Status.PENDING:
        raise ValueError("Teklif artık beklemede değil.")
    offer.status = Offer.Status.REJECTED
    offer.responded_at = timezone.now()
    offer.save(update_fields=["status", "responded_at", "updated_at"])
    create_offer_event(
        offer=offer,
        actor=actor,
        event_type=OfferEvent.Type.REJECTED,
        amount=offer.amount,
        message="Teklif reddedildi.",
    )
    recipient = offer.other_participant(actor)
    create_notification(
        user=recipient,
        actor=actor,
        listing=offer.listing,
        notification_type=Notification.Type.OFFER,
        title="Teklif sonuçlandı",
        body="Karşı taraf teklifi kabul etmedi.",
        link=f"{reverse('listings:offer_center')}?focus={offer.pk}",
    )


@db_transaction.atomic
def finalize_transaction(transaction: Transaction) -> None:
    transaction = Transaction.objects.select_for_update().select_related(
        "listing", "buyer", "seller"
    ).get(pk=transaction.pk)
    if not (transaction.buyer_confirmed and transaction.seller_confirmed):
        return
    if transaction.status == Transaction.Status.COMPLETED:
        return
    transaction.status = Transaction.Status.COMPLETED
    transaction.completed_at = timezone.now()
    transaction.save(update_fields=["status", "completed_at", "updated_at"])
    record_transaction_event(
        transaction=transaction, event_type=TransactionEvent.Type.COMPLETED,
        note="İşlem iki tarafın onayıyla tamamlandı.",
    )
    Listing.objects.filter(pk=transaction.listing_id).update(
        status=Listing.Status.COMPLETED,
        updated_at=timezone.now(),
    )
    from .matching import sync_listing_matches

    sync_listing_matches(transaction.listing, notify=False)
    for user_id in {transaction.buyer_id, transaction.seller_id}:
        from apps.accounts.models import User

        User.objects.filter(pk=user_id).update(completed_transactions=F("completed_transactions") + 1)

    for recipient in (transaction.buyer, transaction.seller):
        other = transaction.seller if recipient.pk == transaction.buyer_id else transaction.buyer
        create_notification(
            user=recipient,
            actor=other,
            listing=transaction.listing,
            notification_type=Notification.Type.REVIEW,
            title="İşlem tamamlandı",
            body="Deneyimini puanlayarak İlan Şehri güven topluluğuna katkı sağlayabilirsin.",
            link=reverse("listings:transaction_detail", kwargs={"public_id": transaction.public_id}),
        )


def refresh_user_rating(user) -> None:
    stats = Review.objects.filter(reviewed_user=user, is_visible=True).aggregate(
        average=Avg("rating"),
        count=Count("id"),
    )
    user.average_rating = Decimal(str(stats["average"] or 0)).quantize(Decimal("0.01"))
    user.rating_count = stats["count"] or 0
    user.save(update_fields=["average_rating", "rating_count"])
