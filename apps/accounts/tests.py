from django.test import TestCase, override_settings
from django.urls import reverse

from .models import User, VerificationCode


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
                "accept_terms": "on",
                "password1": "GucluTestSifresi_2026",
                "password2": "GucluTestSifresi_2026",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="ahmettest").exists())
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertContains(response, "Hoş geldin")

    def test_user_can_update_profile(self):
        user = User.objects.create_user(username="profile", password="StrongPass_2026")
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "first_name": "Profil",
                "last_name": "Kullanıcı",
                "email": "profile@example.com",
                "phone": "05551112233",
                "user_type": User.UserType.INDIVIDUAL,
                "city": "Şanlıurfa",
                "district": "Haliliye",
                "neighborhood": "Sırrın",
                "bio": "Güvenilir kullanıcı",
            },
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))
        user.refresh_from_db()
        self.assertEqual(user.neighborhood, "Sırrın")

    @override_settings(VERIFICATION_DEBUG_CODE=True)
    def test_verification_code_marks_phone_verified(self):
        user = User.objects.create_user(username="verify", password="StrongPass_2026", phone="05550000000")
        code = VerificationCode.issue(
            user=user,
            channel=VerificationCode.Channel.PHONE,
            destination=user.phone,
            raw_code="123456",
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:verification_confirm"),
            {"channel": VerificationCode.Channel.PHONE, "code": "123456"},
        )
        self.assertRedirects(response, reverse("accounts:verification"))
        user.refresh_from_db()
        code.refresh_from_db()
        self.assertTrue(user.is_phone_verified)
        self.assertIsNotNone(code.consumed_at)
