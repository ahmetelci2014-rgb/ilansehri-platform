from __future__ import annotations

from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Avg, Count, F
from django.urls import reverse
from django.utils import timezone

from .models import (
    Favorite,
    Listing,
    ListingPriceHistory,
    Notification,
    Offer,
    OfferEvent,
    Review,
    Transaction,
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
    return Notification.objects.create(
        user=user,
        actor=actor,
        listing=listing,
        notification_type=notification_type,
        title=title,
        body=body[:320],
        link=link[:320],
    )


def create_offer_event(*, offer, actor, event_type, amount=None, message=""):
    return OfferEvent.objects.create(
        offer=offer,
        actor=actor,
        event_type=event_type,
        amount=amount,
        message=(message or "")[:1200],
    )


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
        create_notification(
            user=recipient,
            actor=listing.owner,
            listing=listing,
            notification_type=Notification.Type.FOLLOW,
            title=f"{listing.owner.display_name} yeni ilan yayınladı",
            body=listing.title,
            link=listing.get_absolute_url(),
        )
        created += 1
    return created


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
        create_notification(
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
        link=reverse("listings:offer_center"),
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
        },
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
        link=reverse("listings:offer_center"),
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
    Listing.objects.filter(pk=transaction.listing_id).update(
        status=Listing.Status.COMPLETED,
        updated_at=timezone.now(),
    )
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
