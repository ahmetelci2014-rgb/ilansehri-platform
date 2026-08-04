from django.db.models import Q

from .models import Message, Notification


def notification_counts(request):
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0, "unread_message_count": 0}
    unread_messages = Message.objects.filter(
        Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
        is_read=False,
    ).exclude(sender=request.user).count()
    return {
        "unread_notification_count": Notification.objects.filter(user=request.user, is_read=False).count(),
        "unread_message_count": unread_messages,
    }
