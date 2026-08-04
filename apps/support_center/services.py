from __future__ import annotations

from django.urls import reverse
from django.utils import timezone

from apps.listings.models import Notification
from apps.listings.services import create_notification

from .models import StaffActionLog, SupportReply, SupportTicket


def log_staff_action(*, actor, action, summary, target=None, metadata=None):
    return StaffActionLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        target_type=target.__class__.__name__ if target else "",
        target_id=str(getattr(target, "pk", "")) if target else "",
        summary=summary[:300],
        metadata=metadata or {},
    )


def add_ticket_reply(*, ticket: SupportTicket, author, message: str, internal=False, update_status=True):
    reply = SupportReply.objects.create(
        ticket=ticket,
        author=author,
        message=message.strip(),
        is_internal_note=internal,
    )
    ticket.last_reply_at = timezone.now()
    fields = ["last_reply_at", "updated_at"]
    if update_status and not internal and getattr(author, "is_staff", False):
        ticket.status = SupportTicket.Status.WAITING_USER
        fields.append("status")
        create_notification(
            user=ticket.user,
            actor=author,
            notification_type=Notification.Type.SYSTEM,
            title="Destek talebine yanıt geldi",
            body=ticket.subject,
            link=reverse("support_center:ticket_detail", kwargs={"public_id": ticket.public_id}),
        )
    elif update_status and not internal and author == ticket.user and ticket.status in {
        SupportTicket.Status.WAITING_USER,
        SupportTicket.Status.RESOLVED,
    }:
        ticket.status = SupportTicket.Status.IN_PROGRESS
        ticket.resolved_at = None
        fields.extend(["status", "resolved_at"])
    ticket.save(update_fields=list(dict.fromkeys(fields)))
    return reply
