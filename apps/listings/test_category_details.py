from django.core.management import call_command
from django.test import TestCase

from .catalog import (
    category_detail_fields,
    category_detail_profile,
)
from .forms import ListingForm
from .models import Category, Listing


class CategoryDetailContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_categories", verbosity=0)

    def form_data(self, category, kind, **extra):
        data = {
            "kind": kind,
            "action": Listing.Action.SELL,
            "management_mode": Listing.ManagementMode.SELF,
            "category": str(category.pk),
            "title": "Profesyonel test ilanı",
            "description": "Kategoriye göre ayrıntı alanlarının test ilanıdır.",
            "price": "10000.00",
            "city": "Şanlıurfa",
            "district": "Karaköprü",
            "neighborhood": "Akpıyar",
        }
        data.update(extra)
        return data

    def test_vehicle_parts_do_not_require_running_vehicle_fields(self):
        category = Category.objects.get(name="Yedek Parça", parent__name="Araç")

        fields = set(category_detail_fields(category))

        self.assertEqual(
            category_detail_profile(category),
            "vehicle_parts",
        )
        self.assertNotIn("mileage", fields)
        self.assertNotIn("fuel_type", fields)
        self.assertNotIn("transmission", fields)
        self.assertNotIn("model_year", fields)

        form = ListingForm(
            data=self.form_data(
                category,
                Listing.Kind.VEHICLE,
                condition="Yeni",
            )
        )

        self.assertTrue(
            form.is_valid(),
            form.errors.as_json(),
        )

    def test_automobile_still_requires_core_vehicle_details(self):
        category = Category.objects.get(name="Otomobil", parent__name="Araç")

        form = ListingForm(
            data=self.form_data(
                category,
                Listing.Kind.VEHICLE,
                brand="Toyota",
                model_name="Corolla",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("model_year", form.errors)

    def test_land_does_not_require_room_count(self):
        category = Category.objects.get(name="Satılık Arsa", parent__name="Emlak")

        fields = set(category_detail_fields(category))

        self.assertEqual(
            category_detail_profile(category),
            "estate_land",
        )
        self.assertIn("area_m2", fields)
        self.assertNotIn("room_count", fields)
        self.assertNotIn("floor_location", fields)
        self.assertNotIn("heating_type", fields)

        form = ListingForm(
            data=self.form_data(
                category,
                Listing.Kind.REAL_ESTATE,
                area_m2="1250",
            )
        )

        self.assertTrue(
            form.is_valid(),
            form.errors.as_json(),
        )

    def test_food_product_does_not_require_product_condition(self):
        category = Category.objects.get(name="Yeme & İçme", parent__name="Ürün & Eşya")

        self.assertEqual(
            category_detail_profile(category),
            "product_food",
        )

        form = ListingForm(
            data=self.form_data(
                category,
                Listing.Kind.PRODUCT,
            )
        )

        self.assertTrue(
            form.is_valid(),
            form.errors.as_json(),
        )

    def test_category_options_export_frontend_contract(self):
        html = str(ListingForm()["category"])

        self.assertIn(
            'data-category-profile="vehicle_parts"',
            html,
        )
        self.assertIn(
            "data-category-fields=",
            html,
        )
