from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.listings.models import Category


CATEGORIES = {
    "Ürün & Eşya": ["Elektronik", "Ev & Mobilya", "Giyim", "Bebek & Çocuk", "Hobi & Spor", "Makine & Ekipman"],
    "Araç": ["Otomobil", "Motosiklet", "Ticari Araç", "Kiralık Araç", "Yedek Parça"],
    "Emlak": ["Konut", "İşyeri", "Arsa", "Günlük Kiralık", "Devren İşletme"],
    "Hizmet": ["Tamir & Tadilat", "Temizlik", "Nakliye", "Özel Ders", "Çocuk Bakımı", "Yaşlı Bakımı", "Organizasyon"],
    "İş": ["İş İlanları", "İş Arayanlar", "Günlük İşler", "Uzaktan Çalışma"],
    "İhtiyaçlar": ["Ürün Arıyorum", "Hizmet Arıyorum", "Kiralık Arıyorum", "Takas Arıyorum"],
}


class Command(BaseCommand):
    help = "İlan Şehri başlangıç kategorilerini oluşturur."

    def handle(self, *args, **options):
        created_count = 0
        for order, (parent_name, children) in enumerate(CATEGORIES.items(), start=1):
            parent, created = Category.objects.get_or_create(
                slug=slugify(parent_name),
                defaults={"name": parent_name, "sort_order": order},
            )
            created_count += int(created)
            for child_order, child_name in enumerate(children, start=1):
                _, child_created = Category.objects.get_or_create(
                    slug=slugify(f"{parent_name}-{child_name}"),
                    defaults={
                        "name": child_name,
                        "parent": parent,
                        "sort_order": child_order,
                    },
                )
                created_count += int(child_created)
        self.stdout.write(self.style.SUCCESS(f"{created_count} yeni kategori oluşturuldu."))
