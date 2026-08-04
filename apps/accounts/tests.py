from django.test import TestCase
from django.urls import reverse

from .models import User


class AccountFlowTests(TestCase):
    def test_user_can_sign_up_and_reach_dashboard(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "ahmettest",
                "first_name": "Ahmet",
                "last_name": "Test",
                "email": "ahmet@example.com",
                "phone": "05550000000",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "user_type": User.UserType.INDIVIDUAL,
                "password1": "GucluTestSifresi_2026",
                "password2": "GucluTestSifresi_2026",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="ahmettest").exists())
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertContains(response, "Hoş geldin")
