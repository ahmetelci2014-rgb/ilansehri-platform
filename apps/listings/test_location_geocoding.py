from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .geocoding import parse_nominatim_geocodejson
from .locations import (
    canonicalize_city,
    canonicalize_district,
    canonicalize_neighborhood,
)


class LocationNormalizationTests(TestCase):
    def test_turkish_location_names_are_canonicalized(self):
        self.assertEqual(
            canonicalize_city("ŞANLIURFA"),
            "Şanlıurfa",
        )
        self.assertEqual(
            canonicalize_district(
                "Şanlıurfa",
                "Karaköprü İlçesi",
            ),
            "Karaköprü",
        )
        self.assertEqual(
            canonicalize_neighborhood(
                "Şanlıurfa",
                "Karaköprü",
                "Akpıyar Mahallesi",
            ),
            "Akpıyar",
        )

    def test_unknown_neighborhood_is_not_rejected_or_destroyed(self):
        self.assertEqual(
            canonicalize_neighborhood(
                "Şanlıurfa",
                "Karaköprü",
                "Yeni Gerçek Mahallesi",
            ),
            "Yeni Gerçek",
        )


class ReverseGeocodingParserTests(TestCase):
    def test_geocodejson_becomes_city_district_neighborhood(self):
        payload = {
            "geocoding": {
                "attribution": "© OpenStreetMap contributors",
            },
            "features": [
                {
                    "properties": {
                        "geocoding": {
                            "country": "Türkiye",
                            "state": "Şanlıurfa",
                            "district": "Karaköprü İlçesi",
                            "locality": "Akpıyar Mahallesi",
                            "admin": {
                                "level4": "Şanlıurfa",
                                "level6": "Karaköprü İlçesi",
                                "level10": "Akpıyar Mahallesi",
                            },
                        }
                    }
                }
            ],
        }

        result = parse_nominatim_geocodejson(payload)

        self.assertEqual(result["city"], "Şanlıurfa")
        self.assertEqual(result["district"], "Karaköprü")
        self.assertEqual(result["neighborhood"], "Akpıyar")
        self.assertIn("OpenStreetMap", result["attribution"])


class ReverseLocationEndpointTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="location-user",
            password="StrongPass_2026",
        )
        self.client.force_login(self.user)

    @patch("apps.listings.views.reverse_geocode")
    def test_endpoint_returns_only_coarse_address(self, mocked):
        mocked.return_value = {
            "city": "Şanlıurfa",
            "district": "Karaköprü",
            "neighborhood": "Akpıyar",
            "attribution": "© OpenStreetMap contributors",
        }

        response = self.client.get(
            reverse("listings:reverse_location"),
            {
                "lat": "37.16740",
                "lng": "38.79550",
            },
        )

        self.assertEqual(response.status_code, 200)

        payload = response.json()

        self.assertEqual(payload["city"], "Şanlıurfa")
        self.assertEqual(payload["district"], "Karaköprü")
        self.assertEqual(payload["neighborhood"], "Akpıyar")

        # Tam açık adres, sokak veya ev numarası dönmemeli.
        self.assertNotIn("road", payload)
        self.assertNotIn("house_number", payload)

    def test_endpoint_rejects_invalid_coordinates(self):
        response = self.client.get(
            reverse("listings:reverse_location"),
            {
                "lat": "999",
                "lng": "999",
            },
        )

        self.assertEqual(response.status_code, 400)
