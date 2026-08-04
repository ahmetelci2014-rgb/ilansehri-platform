from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AccountClosureRequest, User, UserFollow, VerificationCode


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


    def test_user_can_follow_and_unfollow_seller(self):
        follower = User.objects.create_user(username="follower", password="StrongPass_2026")
        seller = User.objects.create_user(username="seller", password="StrongPass_2026")
        self.client.force_login(follower)
        url = reverse("accounts:toggle_follow", kwargs={"pk": seller.pk})
        self.client.post(url)
        self.assertTrue(UserFollow.objects.filter(follower=follower, seller=seller).exists())
        profile = self.client.get(reverse("accounts:public_profile", kwargs={"username": seller.username}))
        self.assertContains(profile, "1")
        self.client.post(url)
        self.assertFalse(UserFollow.objects.filter(follower=follower, seller=seller).exists())

    def test_dashboard_reports_profile_completion(self):
        user = User.objects.create_user(
            username="profile-score",
            password="StrongPass_2026",
            first_name="Ahmet",
            last_name="Kullanıcı",
            email="ahmet@example.com",
            phone="05550000000",
            city="Şanlıurfa",
            district="Karaköprü",
            bio="Güvenilir yerel kullanıcı",
            is_phone_verified=True,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.context["profile_completion"], 50)
        self.assertEqual(len(response.context["profile_steps"]), 8)
        self.assertContains(response, "Profil doluluğu")

    def test_account_data_export_requires_login_and_downloads_json(self):
        login_url = f"{reverse('login')}?next={reverse('accounts:export_data')}"
        response = self.client.get(reverse("accounts:export_data"))
        self.assertRedirects(response, login_url)
        user = User.objects.create_user(username="export-user", password="StrongPass_2026", email="export@example.com")
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:export_data"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertContains(response, "export-user")

    def test_user_can_request_and_cancel_account_closure(self):
        user = User.objects.create_user(username="close-user", password="StrongPass_2026")
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:request_closure"),
            {
                "password": "StrongPass_2026",
                "reason": "Artık kullanmıyorum.",
                "confirmation": "on",
            },
        )
        self.assertRedirects(response, reverse("accounts:settings"))
        closure = AccountClosureRequest.objects.get(user=user)
        self.assertEqual(closure.status, AccountClosureRequest.Status.PENDING)
        self.client.post(reverse("accounts:cancel_closure"))
        closure.refresh_from_db()
        self.assertEqual(closure.status, AccountClosureRequest.Status.CANCELLED)

    def test_wrong_password_does_not_create_closure_request(self):
        user = User.objects.create_user(username="safe-user", password="StrongPass_2026")
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:request_closure"),
            {"password": "yanlis-sifre", "confirmation": "on"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AccountClosureRequest.objects.filter(user=user).exists())
        self.assertContains(response, "Şifren doğru değil")

    def test_password_reset_page_is_available(self):
        response = self.client.get(reverse("password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Şifreni yeniden oluştur")

