from django.core.management.base import BaseCommand

from apps.listings.matching import sync_listing_matches
from apps.listings.models import Listing


class Command(BaseCommand):
    help = "Yayındaki ilanlar için Arıyorum–Satıyorum eşleşmelerini yeniden hesaplar."

    def add_arguments(self, parser):
        parser.add_argument("--notify", action="store_true", help="Yeni eşleşmeler için bildirim oluştur.")
        parser.add_argument("--limit", type=int, default=0, help="İşlenecek ilan sayısı; 0 tümü.")

    def handle(self, *args, **options):
        queryset = Listing.objects.filter(status=Listing.Status.PUBLISHED).order_by("pk")
        if options["limit"] > 0:
            queryset = queryset[: options["limit"]]
        scanned = created = updated = deleted = 0
        for listing in queryset.iterator(chunk_size=100):
            result = sync_listing_matches(listing, notify=options["notify"])
            scanned += 1
            created += result["created"]
            updated += result["updated"]
            deleted += result.get("deleted", 0)
        self.stdout.write(
            self.style.SUCCESS(
                f"İşlenen ilan: {scanned} · Yeni eşleşme: {created} · "
                f"Güncellenen: {updated} · Temizlenen: {deleted}"
            )
        )
