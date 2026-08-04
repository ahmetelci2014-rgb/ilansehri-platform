from __future__ import annotations

from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Avg, Count, F
from django.urls import reverse
from django.utils import timezone

from .models import Listing, Notification, Offer, Review, Transaction


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


@db_transaction.atomic
def accept_offer(*, offer: Offer, actor) -> Transaction:
    locked_offer = (
        Offer.objects.select_for_update()
        .select_related("listing", "listing__owner", "sender")
        .get(pk=offer.pk)
    )
    listing = Listing.objects.select_for_update().get(pk=locked_offer.listing_id)
    if actor.pk != listing.owner_id:
        raise PermissionError("Bu teklifi yalnız ilan sahibi kabul edebilir.")
    if locked_offer.status != Offer.Status.PENDING:
        raise ValueError("Teklif artık beklemede değil.")
    if listing.status not in {Listing.Status.PUBLISHED, Listing.Status.PAUSED}:
        raise ValueError("Bu ilan için işlem başlatılamaz.")

    locked_offer.status = Offer.Status.ACCEPTED
    locked_offer.responded_at = timezone.now()
    locked_offer.save(update_fields=["status", "responded_at", "updated_at"])
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

    create_notification(
        user=locked_offer.sender,
        actor=actor,
        listing=listing,
        notification_type=Notification.Type.TRANSACTION,
        title="Teklifin kabul edildi",
        body="Satıcı teklifini kabul etti. Teslim ve işlem adımlarını güvenli işlem ekranından takip et.",
        link=transaction.get_absolute_url(),
    )
    return transaction


def reject_offer(*, offer: Offer, actor) -> None:
    if actor.pk != offer.listing.owner_id:
        raise PermissionError("Bu teklifi yalnız ilan sahibi reddedebilir.")
    if offer.status != Offer.Status.PENDING:
        raise ValueError("Teklif artık beklemede değil.")
    offer.status = Offer.Status.REJECTED
    offer.responded_at = timezone.now()
    offer.save(update_fields=["status", "responded_at", "updated_at"])
    create_notification(
        user=offer.sender,
        actor=actor,
        listing=offer.listing,
        notification_type=Notification.Type.OFFER,
        title="Teklifin sonuçlandı",
        body="İlan sahibi bu teklifi kabul etmedi. Diğer ilanları inceleyebilirsin.",
        link=offer.listing.get_absolute_url(),
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
