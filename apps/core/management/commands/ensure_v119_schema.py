from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import F

from apps.listings.models import Review, Transaction, TransactionEvent


class Command(BaseCommand):
    help = "v1.19 güvenli teslim, işlem olayı ve kör değerlendirme alanlarını geriye uyumlu biçimde doğrular."

    def _columns(self, table_name):
        with connection.cursor() as cursor:
            return {
                item.name
                for item in connection.introspection.get_table_description(cursor, table_name)
            }

    def handle(self, *args, **options):
        existing_tables = set(connection.introspection.table_names())
        created = []

        with connection.schema_editor() as schema_editor:
            event_table = TransactionEvent._meta.db_table
            if event_table not in existing_tables:
                schema_editor.create_model(TransactionEvent)
                existing_tables.add(event_table)
                created.append(event_table)

            transaction_table = Transaction._meta.db_table
            if transaction_table in existing_tables:
                columns = self._columns(transaction_table)
                field_names = (
                    "delivery_type",
                    "delivery_started_at",
                    "handover_code_hash",
                    "handover_code_created_at",
                    "handover_code_attempts",
                    "handover_verified_at",
                    "buyer_confirmed_at",
                    "seller_confirmed_at",
                )
                for field_name in field_names:
                    field = Transaction._meta.get_field(field_name)
                    if field.column not in columns:
                        schema_editor.add_field(Transaction, field)
                        columns.add(field.column)
                        created.append(f"{transaction_table}.{field.column}")

            review_table = Review._meta.db_table
            if review_table in existing_tables:
                columns = self._columns(review_table)
                field = Review._meta.get_field("published_at")
                if field.column not in columns:
                    schema_editor.add_field(Review, field)
                    created.append(f"{review_table}.{field.column}")

        backfilled_reviews = 0
        if Review._meta.db_table in existing_tables:
            backfilled_reviews = Review.objects.filter(
                is_visible=True, published_at__isnull=True
            ).update(published_at=F("created_at"))

        if created:
            message = "v1.19 şema eklentileri oluşturuldu: " + ", ".join(created)
        else:
            message = "v1.19 şeması zaten güncel."
        if backfilled_reviews:
            message += f" {backfilled_reviews} eski görünür değerlendirme yayın tarihiyle tamamlandı."
        self.stdout.write(self.style.SUCCESS(message))
