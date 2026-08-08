from django.db.models import F, Q
from django.utils import timezone

from .locations import CITY_CHOICES
from .location_preference import header_location_context
from .matching import blocked_owner_ids
from .models import Appointment, Favorite, ListingMatch, Message, Notification, Offer


def notification_counts(request):
    location_context = header_location_context(request)
    compare_count = len(request.session.get("compare_listing_ids", [])) if hasattr(request, "session") else 0
    if not request.user.is_authenticated:
        return {
            "unread_notification_count": 0,
            "unread_message_count": 0,
            "header_favorite_count": 0,
            "header_offer_count": 0,
            "header_match_count": 0,
            "header_pending_appointment_count": 0,
            "compare_count": compare_count,
            "header_city_choices": CITY_CHOICES,
            **location_context,
        }
    unread_messages = Message.objects.filter(
        Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
        is_read=False,
    ).exclude(sender=request.user).count()
    now = timezone.now()
    active_pairs = (
        Q(wanted_listing__status="published")
        & Q(offered_listing__status="published")
        & (Q(wanted_listing__expires_at__isnull=True) | Q(wanted_listing__expires_at__gt=now))
        & (Q(offered_listing__expires_at__isnull=True) | Q(offered_listing__expires_at__gt=now))
    )
    excluded_owner_ids = blocked_owner_ids(request.user.pk)
    header_match_count = (
        ListingMatch.objects.filter(
            active_pairs, wanted_listing__owner=request.user, wanted_status=ListingMatch.Status.NEW
        ).exclude(offered_listing__owner_id__in=excluded_owner_ids).count()
        + ListingMatch.objects.filter(
            active_pairs, offered_listing__owner=request.user, offered_status=ListingMatch.Status.NEW
        ).exclude(wanted_listing__owner_id__in=excluded_owner_ids).count()
    )
    return {
        "unread_notification_count": Notification.objects.filter(user=request.user, is_read=False).count(),
        "unread_message_count": unread_messages,
        "header_favorite_count": Favorite.objects.filter(user=request.user).count(),
        "header_match_count": header_match_count,
        "header_offer_count": Offer.objects.filter(status=Offer.Status.PENDING).filter(
            Q(listing__owner=request.user, last_actor=F("sender"))
            | Q(listing__owner=request.user, last_actor__isnull=True)
            | Q(sender=request.user, last_actor=F("listing__owner"))
        ).count(),
        "header_pending_appointment_count": Appointment.objects.filter(
            invitee=request.user,
            status=Appointment.Status.PENDING,
            starts_at__gte=now,
        ).count(),
        "compare_count": compare_count,
        "header_city_choices": CITY_CHOICES,
        **location_context,
    }
