from django.db.models import Q

from .models import Favorite, Message, Notification


def notification_counts(request):
    compare_count = len(request.session.get("compare_listing_ids", [])) if hasattr(request, "session") else 0
    if not request.user.is_authenticated:
        return {
            "unread_notification_count": 0,
            "unread_message_count": 0,
            "header_favorite_count": 0,
            "compare_count": compare_count,
        }
    unread_messages = Message.objects.filter(
        Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
        is_read=False,
    ).exclude(sender=request.user).count()
    return {
        "unread_notification_count": Notification.objects.filter(user=request.user, is_read=False).count(),
        "unread_message_count": unread_messages,
        "header_favorite_count": Favorite.objects.filter(user=request.user).count(),
        "compare_count": compare_count,
    }
