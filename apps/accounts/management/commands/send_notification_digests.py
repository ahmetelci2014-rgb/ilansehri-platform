from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import NotificationPreference
from apps.listings.models import Notification


class Command(BaseCommand):
    help = "Günlük veya haftalık bildirim özeti tercihlerini e-posta olarak gönderir."

    def handle(self, *args, **options):
        now = timezone.now()
        sent = 0
        skipped = 0
        preferences = NotificationPreference.objects.select_related("user").exclude(
            digest_frequency=NotificationPreference.DigestFrequency.OFF
        )
        for preference in preferences.iterator():
            user = preference.user
            if not user.is_active or not user.email or not user.is_email_verified:
                skipped += 1
                continue
            period = (
                timedelta(days=1)
                if preference.digest_frequency == NotificationPreference.DigestFrequency.DAILY
                else timedelta(days=7)
            )
            if preference.last_digest_at and preference.last_digest_at > now - period:
                skipped += 1
                continue
            since = preference.last_digest_at or now - period
            notifications = list(
                Notification.objects.filter(user=user, created_at__gt=since)
                .select_related("listing")
                .order_by("-created_at")[:80]
            )
            notifications = [
                item
                for item in notifications
                if not preference.allows_email(item.notification_type)
            ]
            preference.last_digest_at = now
            preference.save(update_fields=["last_digest_at", "updated_at"])
            if not notifications:
                skipped += 1
                continue
            lines = [
                f"Merhaba {user.display_name},",
                "",
                f"İlan Şehri hesabında {len(notifications)} yeni gelişme var:",
                "",
            ]
            for item in notifications[:30]:
                line = f"• {item.title}"
                if item.body:
                    line += f" — {item.body}"
                if item.link and settings.PUBLIC_BASE_URL:
                    line += f" ({settings.PUBLIC_BASE_URL}{item.link})"
                lines.append(line)
            if len(notifications) > 30:
                lines.append(f"• ve {len(notifications) - 30} bildirim daha")
            lines.extend(
                [
                    "",
                    "Bildirim tercihlerini hesabındaki Bildirim Tercihleri sayfasından değiştirebilirsin.",
                ]
            )
            result = send_mail(
                subject=f"İlan Şehri · {len(notifications)} yeni bildirim",
                message="\n".join(lines),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            sent += int(bool(result))
        self.stdout.write(self.style.SUCCESS(f"Özet gönderilen: {sent} · Atlanan: {skipped}"))
