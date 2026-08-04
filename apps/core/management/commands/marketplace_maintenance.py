from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import VerificationCode
from apps.listings.models import Listing, Notification, SavedSearch
from apps.listings.services import create_notification


class Command(BaseCommand):
    help = "Süresi dolan ilanları kapatır, eski doğrulama kodlarını temizler ve kayıtlı arama uyarılarını üretir."

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
        searches = SavedSearch.objects.filter(alert_enabled=True).select_related("user")
        for saved in searches.iterator():
            params = saved.query_params or {}
            since = saved.last_notified_at or saved.created_at
            qs = Listing.objects.filter(
                status=Listing.Status.PUBLISHED,
                created_at__gt=since,
            ).exclude(owner=saved.user)

            q = str(params.get("q", "")).strip()
            if q:
                qs = qs.filter(
                    Q(title__icontains=q)
                    | Q(description__icontains=q)
                    | Q(category__name__icontains=q)
                    | Q(brand__icontains=q)
                    | Q(model_name__icontains=q)
                )
            exact_filters = {"city": "city", "kind": "kind", "action": "action", "room_count": "room_count"}
            partial_filters = {"district": "district__icontains", "brand": "brand__icontains", "model": "model_name__icontains"}
            for key, lookup in exact_filters.items():
                value = str(params.get(key, "")).strip()
                if value:
                    qs = qs.filter(**{lookup: value})
            for key, lookup in partial_filters.items():
                value = str(params.get(key, "")).strip()
                if value:
                    qs = qs.filter(**{lookup: value})

            decimal_filters = {"min_price": "price__gte", "max_price": "price__lte"}
            for key, lookup in decimal_filters.items():
                value = str(params.get(key, "")).strip()
                if value:
                    try:
                        qs = qs.filter(**{lookup: Decimal(value)})
                    except (InvalidOperation, ValueError):
                        pass
            integer_filters = {
                "min_year": "model_year__gte",
                "max_year": "model_year__lte",
                "max_mileage": "mileage__lte",
                "min_area": "area_m2__gte",
                "max_area": "area_m2__lte",
            }
            for key, lookup in integer_filters.items():
                value = str(params.get(key, "")).strip()
                if value:
                    try:
                        qs = qs.filter(**{lookup: int(value)})
                    except ValueError:
                        pass
            if str(params.get("verified", "")) == "1":
                qs = qs.filter(owner__is_phone_verified=True)
            if str(params.get("managed", "")) == "1":
                qs = qs.filter(management_mode=Listing.ManagementMode.FULL)

            match_count = qs.count()
            if match_count:
                create_notification(
                    user=saved.user,
                    notification_type=Notification.Type.SYSTEM,
                    title=f"{saved.name} aramana uygun yeni ilanlar var",
                    body=f"{match_count} yeni ilan bulundu. Sonuçları görmek için dokun.",
                    link=reverse("listings:list") + "?" + urlencode(
                        {key: value for key, value in params.items() if value}
                    ),
                )
                alert_count += 1
            saved.last_notified_at = now
            saved.save(update_fields=["last_notified_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Bakım tamamlandı: {expired_count} ilan kapatıldı, "
                f"{deleted_codes} doğrulama kaydı temizlendi, {alert_count} arama uyarısı üretildi."
            )
        )
