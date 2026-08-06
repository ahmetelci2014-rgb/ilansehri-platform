from datetime import timedelta
from urllib.parse import urlencode

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import VerificationCode
from apps.listings.models import Appointment, Listing, Notification, SavedSearch, SavedSearchMatch
from apps.listings.search_alerts import apply_listing_filters, attach_nearby_distances, saved_search_result_params
from apps.listings.services import create_notification, publish_due_reviews, send_appointment_reminders


class Command(BaseCommand):
    help = "İlan, doğrulama, günlük arama ve kör değerlendirme bakımını çalıştırır."

    def handle(self, *args, **options):
        now = timezone.now()
        expired_count = Listing.objects.filter(
            status=Listing.Status.PUBLISHED,
            expires_at__isnull=False,
            expires_at__lte=now,
        ).update(status=Listing.Status.EXPIRED, updated_at=now)

        deleted_codes, _ = VerificationCode.objects.filter(
            created_at__lt=now - timedelta(days=7)
        ).delete()

        alert_count = 0
        match_count = 0
        due_before = now - timedelta(hours=23)
        searches = (
            SavedSearch.objects.filter(
                alert_enabled=True,
                alert_frequency=SavedSearch.AlertFrequency.DAILY,
                user__is_active=True,
            )
            .filter(Q(last_checked_at__isnull=True) | Q(last_checked_at__lte=due_before))
            .select_related("user")
        )
        for saved in searches.iterator():
            params = saved.query_params or {}
            since = saved.last_checked_at or saved.created_at
            qs = (
                Listing.objects.filter(
                    status=Listing.Status.PUBLISHED,
                )
                .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
                .filter(Q(published_at__gt=since) | Q(published_at__isnull=True, created_at__gt=since))
                .exclude(owner=saved.user)
                .select_related("owner", "category")
            )
            qs = apply_listing_filters(qs, params, user=saved.user)
            candidates = attach_nearby_distances(qs, params)

            new_matches = []
            for listing in candidates:
                match, created = SavedSearchMatch.objects.get_or_create(
                    saved_search=saved,
                    listing=listing,
                )
                if created:
                    new_matches.append(match)

            if new_matches:
                result_url = reverse("listings:list")
                query_string = urlencode(saved_search_result_params(params))
                if query_string:
                    result_url += "?" + query_string
                notification = create_notification(
                    user=saved.user,
                    notification_type=Notification.Type.SEARCH_ALERT,
                    title=f"{saved.name} günlük arama özeti",
                    body=f"{len(new_matches)} yeni ilan bulundu. Sonuçları görmek için dokun.",
                    link=result_url,
                )
                if notification is not None:
                    notified_at = timezone.now()
                    SavedSearchMatch.objects.filter(pk__in=[item.pk for item in new_matches]).update(
                        notified_at=notified_at
                    )
                    saved.last_notified_at = notified_at
                    alert_count += 1
                    match_count += len(new_matches)

            saved.last_checked_at = now
            update_fields = ["last_checked_at", "updated_at"]
            if saved.last_notified_at:
                update_fields.append("last_notified_at")
            saved.save(update_fields=update_fields)

        published_review_count = publish_due_reviews(now=now)
        expired_appointment_count = Appointment.objects.filter(
            status=Appointment.Status.PENDING,
            starts_at__lt=now,
        ).update(status=Appointment.Status.CANCELLED, responded_at=now, updated_at=now)
        appointment_reminder_count = send_appointment_reminders(now=now)

        self.stdout.write(
            self.style.SUCCESS(
                f"Bakım tamamlandı: {expired_count} ilan kapatıldı, "
                f"{deleted_codes} doğrulama kaydı temizlendi, "
                f"{alert_count} günlük arama özeti ve {match_count} tekil eşleşme üretildi, "
                f"{published_review_count} bekleyen değerlendirme yayınlandı, "
                f"{expired_appointment_count} süresi geçen randevu kapatıldı ve "
                f"{appointment_reminder_count} randevu hatırlatması gönderildi."
            )
        )
