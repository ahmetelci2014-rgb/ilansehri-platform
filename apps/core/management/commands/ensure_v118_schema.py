from django.core.management.base import BaseCommand
from django.db import connection

from apps.accounts.models import AccountRiskEvent, UserReport
from apps.listings.models import ListingImage


class Command(BaseCommand):
    help = "v1.18 güvenlik tablolarını ve görsel parmak izi alanını geriye uyumlu biçimde doğrular."

    def handle(self, *args, **options):
        existing_tables = set(connection.introspection.table_names())
        created = []

        with connection.schema_editor() as schema_editor:
            for model in (UserReport, AccountRiskEvent):
                table_name = model._meta.db_table
                if table_name not in existing_tables:
                    schema_editor.create_model(model)
                    existing_tables.add(table_name)
                    created.append(table_name)

            image_table = ListingImage._meta.db_table
            if image_table in existing_tables:
                with connection.cursor() as cursor:
                    columns = {
                        item.name
                        for item in connection.introspection.get_table_description(cursor, image_table)
                    }
                fingerprint_field = ListingImage._meta.get_field("fingerprint")
                if fingerprint_field.column not in columns:
                    schema_editor.add_field(ListingImage, fingerprint_field)
                    created.append(f"{image_table}.{fingerprint_field.column}")

        if created:
            self.stdout.write(self.style.SUCCESS("v1.18 şema eklentileri oluşturuldu: " + ", ".join(created)))
        else:
            self.stdout.write(self.style.SUCCESS("v1.18 şeması zaten güncel."))
