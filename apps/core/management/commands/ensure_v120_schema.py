from django.core.management.base import BaseCommand
from django.db import connection

from apps.listings.models import Appointment


class Command(BaseCommand):
    help = "v1.20 güvenli randevu tablosunu geriye uyumlu biçimde doğrular."

    def handle(self, *args, **options):
        existing_tables = set(connection.introspection.table_names())
        table_name = Appointment._meta.db_table
        if table_name in existing_tables:
            self.stdout.write(self.style.SUCCESS("v1.20 randevu şeması zaten güncel."))
            return

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Appointment)
        self.stdout.write(self.style.SUCCESS(f"v1.20 randevu tablosu oluşturuldu: {table_name}"))
