from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError

from apps.ai_listing.models import AISettings


class Command(BaseCommand):
    help = "İlan Şehri yapay zekâ ilan sağlayıcısını Google Gemini olarak ayarlar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--enable",
            action="store_true",
            help="GEMINI_API_KEY mevcutsa özelliği aynı anda etkinleştirir.",
        )
        parser.add_argument(
            "--model",
            default="",
            help="Gemini model adı. Varsayılan: GEMINI_MODEL veya gemini-3.6-flash.",
        )

    def handle(self, *args, **options):
        model = (
            str(options.get("model") or "").strip()
            or os.getenv("GEMINI_MODEL", "").strip()
            or "gemini-3.6-flash"
        )
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if options.get("enable") and not api_key:
            raise CommandError(
                "Özellik etkinleştirilemedi: GEMINI_API_KEY .env dosyasında tanımlı değil."
            )

        config = AISettings.load()
        config.provider = AISettings.Provider.GEMINI
        config.model_name = model
        if options.get("enable"):
            config.is_enabled = True
        config.save(update_fields=["provider", "model_name", "is_enabled", "updated_at"])

        state = "açık" if config.is_enabled else "kapalı"
        self.stdout.write(
            self.style.SUCCESS(
                f"Gemini sağlayıcısı seçildi. Model: {model}. AI özelliği: {state}."
            )
        )
        if not config.is_enabled:
            self.stdout.write(
                "API bağlantısını test ettikten sonra komutu --enable ile yeniden çalıştırabilirsiniz."
            )
