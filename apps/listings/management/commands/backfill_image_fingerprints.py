import hashlib

from django.core.management.base import BaseCommand

from apps.listings.models import ListingImage


class Command(BaseCommand):
    help = "Parmak izi bulunmayan mevcut ilan görsellerini güvenli biçimde tamamlar."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=5000)

    def handle(self, *args, **options):
        limit = max(1, min(options["limit"], 50000))
        queryset = ListingImage.objects.filter(fingerprint="").only("pk", "image")[:limit]
        updated = 0
        failed = 0
        for image in queryset.iterator(chunk_size=100):
            try:
                image.image.open("rb")
                digest = hashlib.sha256(image.image.read()).hexdigest()
                image.image.close()
                ListingImage.objects.filter(pk=image.pk, fingerprint="").update(fingerprint=digest)
                updated += 1
            except (OSError, ValueError):
                failed += 1
        self.stdout.write(
            self.style.SUCCESS(f"Görsel parmak izi: {updated} güncellendi, {failed} okunamadı.")
        )
