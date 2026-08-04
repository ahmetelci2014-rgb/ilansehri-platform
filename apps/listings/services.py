from .models import Notification


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
    """Tek noktadan güvenli bildirim oluşturur."""
    if user is None:
        return None
    if actor is not None and actor == user:
        return None
    return Notification.objects.create(
        user=user,
        actor=actor,
        listing=listing,
        notification_type=notification_type,
        title=title,
        body=body,
        link=link,
    )
