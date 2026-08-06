from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.listings.models import Category


# Kökler Listing.Kind ile aynı sırayı izler. Mevcut kayıtlar silinmez; yeni alt
# kategoriler tekrar çalıştırılabilir biçimde eklenir veya güncellenir.
CATEGORIES = (
    (
        "Ürün & Eşya", "▣",
        (
            "Cep Telefonu & Aksesuar", "Bilgisayar & Tablet", "TV & Ses Sistemleri",
            "Fotoğraf & Kamera", "Oyun & Konsol", "Beyaz Eşya", "Küçük Ev Aletleri",
            "Ev & Mobilya", "Bahçe & Yapı Market", "Giyim & Aksesuar", "Ayakkabı & Çanta",
            "Anne, Bebek & Çocuk", "Hobi & Koleksiyon", "Spor & Outdoor", "Kitap & Müzik",
            "Ofis & Kırtasiye", "Makine & Ekipman", "Yeme & İçme", "Diğer Ürünler",
        ),
    ),
    (
        "Araç", "🚘",
        (
            "Otomobil", "SUV & Pick-up", "Motosiklet", "Minivan & Panelvan", "Ticari Araç",
            "Elektrikli Araç", "Karavan", "Deniz Araçları", "Tarım Araçları", "İş Makineleri",
            "Kiralık Araç", "Yedek Parça", "Jant & Lastik", "Araç Aksesuarı",
        ),
    ),
    (
        "Emlak", "⌂",
        (
            "Satılık Daire", "Kiralık Daire", "Müstakil Ev & Villa", "Rezidans", "Günlük Kiralık",
            "Satılık Arsa", "Kiralık İşyeri", "Satılık İşyeri", "Ofis", "Dükkan & Mağaza",
            "Depo & Antrepo", "Tarla & Bahçe", "Devren İşletme", "Turistik Tesis", "Diğer Emlak",
        ),
    ),
    (
        "Hizmet", "🛠",
        (
            "Tamir & Teknik Servis", "Tadilat & Dekorasyon", "Temizlik", "Nakliye & Taşıma",
            "Özel Ders & Eğitim", "Yazılım & Tasarım", "Fotoğraf & Video", "Organizasyon",
            "Güzellik & Bakım", "Çocuk Bakımı", "Yaşlı & Hasta Bakımı", "Evcil Hayvan Hizmetleri",
            "Oto Servis & Bakım", "Hukuk & Danışmanlık", "Muhasebe & Finans", "Diğer Hizmetler",
        ),
    ),
    (
        "İş", "💼",
        (
            "Satış & Pazarlama", "Mağaza & Perakende", "Yeme & İçme", "Ofis & Yönetim",
            "Teknik & Üretim", "Şoför & Kurye", "Temizlik & Güvenlik", "Sağlık", "Eğitim",
            "Yazılım & Teknoloji", "İnşaat", "Günlük & Dönemsel İş", "Uzaktan Çalışma",
            "Staj", "İş Arayanlar",
        ),
    ),
    (
        "İhtiyaçlar", "◎",
        (
            "Ürün Arıyorum", "Araç Arıyorum", "Kiralık Ev Arıyorum", "Satılık Ev Arıyorum",
            "Hizmet Arıyorum", "Usta Arıyorum", "Çalışan Arıyorum", "İş Arıyorum",
            "Takas Arıyorum", "Ortak Arıyorum", "Diğer İhtiyaçlar",
        ),
    ),
)


class Command(BaseCommand):
    help = "İlan Şehri profesyonel kategori kataloğunu oluşturur ve günceller."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for root_order, (parent_name, parent_icon, children) in enumerate(CATEGORIES, start=1):
            parent_slug = slugify(parent_name)
            parent, created = Category.objects.get_or_create(
                slug=parent_slug,
                defaults={
                    "name": parent_name,
                    "icon": parent_icon,
                    "sort_order": root_order,
                    "is_active": True,
                },
            )
            created_count += int(created)
            changed = False
            for field, value in {
                "name": parent_name,
                "icon": parent_icon,
                "sort_order": root_order,
                "is_active": True,
                "parent": None,
            }.items():
                if getattr(parent, field) != value:
                    setattr(parent, field, value)
                    changed = True
            if changed:
                parent.save()
                updated_count += 1

            for child_order, child_name in enumerate(children, start=1):
                child_slug = slugify(f"{parent_name}-{child_name}")
                child, child_created = Category.objects.get_or_create(
                    slug=child_slug,
                    defaults={
                        "name": child_name,
                        "parent": parent,
                        "icon": parent_icon,
                        "sort_order": child_order,
                        "is_active": True,
                    },
                )
                created_count += int(child_created)
                child_changed = False
                for field, value in {
                    "name": child_name,
                    "parent": parent,
                    "icon": parent_icon,
                    "sort_order": child_order,
                    "is_active": True,
                }.items():
                    if getattr(child, field) != value:
                        setattr(child, field, value)
                        child_changed = True
                if child_changed:
                    child.save()
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Kategori kataloğu hazır: {created_count} yeni, {updated_count} güncellenen kayıt."
            )
        )
