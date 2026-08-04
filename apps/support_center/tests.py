from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.listings.models import Notification

from .models import StaffActionLog, SupportReply, SupportTicket


class SupportCenterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="destek_kullanici", password="Test1234!")
        self.other = User.objects.create_user(username="baska_kullanici", password="Test1234!")
        self.staff = User.objects.create_user(username="destek_personel", password="Test1234!", is_staff=True)

    def test_user_can_create_and_view_own_ticket(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("support_center:ticket_create"),
            {
                "category": SupportTicket.Category.TECHNICAL,
                "subject": "İlan sayfası açılmıyor",
                "description": "İlan detayına girince sayfa yüklenmiyor ve tekrar ana sayfaya dönüyor.",
                "related_listing": "",
                "related_transaction": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket = SupportTicket.objects.get(user=self.user)
        self.assertEqual(response.url, ticket.get_absolute_url())
        detail = self.client.get(ticket.get_absolute_url())
        self.assertContains(detail, ticket.subject)

    def test_user_cannot_view_another_users_ticket(self):
        ticket = SupportTicket.objects.create(
            user=self.other,
            category=SupportTicket.Category.OTHER,
            subject="Başka kullanıcı talebi",
            description="Bu talep yalnız sahibi tarafından görüntülenmelidir.",
        )
        self.client.force_login(self.user)
        response = self.client.get(ticket.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_staff_reply_notifies_user_and_internal_note_is_hidden(self):
        ticket = SupportTicket.objects.create(
            user=self.user,
            category=SupportTicket.Category.ACCOUNT,
            subject="Doğrulama sorunu",
            description="Telefon doğrulama kodu gelmedi.",
        )
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("support_center:staff_update", kwargs={"public_id": ticket.public_id}),
            {
                "status": SupportTicket.Status.IN_PROGRESS,
                "priority": SupportTicket.Priority.HIGH,
                "assigned_to": self.staff.pk,
                "public_reply": "Telefon numaranı kontrol edip yeniden kod isteyebilirsin.",
                "internal_note": "SMS sağlayıcı kaydı ayrıca kontrol edilsin.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Notification.objects.filter(user=self.user, title__icontains="Destek").exists())
        self.assertEqual(SupportReply.objects.filter(ticket=ticket).count(), 2)
        self.assertTrue(StaffActionLog.objects.filter(target_id=str(ticket.pk)).exists())

        self.client.force_login(self.user)
        detail = self.client.get(ticket.get_absolute_url())
        self.assertContains(detail, "Telefon numaranı kontrol")
        self.assertNotContains(detail, "SMS sağlayıcı kaydı")

    def test_user_reply_reopens_waiting_ticket(self):
        ticket = SupportTicket.objects.create(
            user=self.user,
            category=SupportTicket.Category.LISTING,
            subject="İlan incelemesi",
            description="İlanımın neden beklediğini öğrenmek istiyorum.",
            status=SupportTicket.Status.WAITING_USER,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("support_center:ticket_reply", kwargs={"public_id": ticket.public_id}),
            {"message": "İstenen bilgileri profilimde güncelledim."},
        )
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, SupportTicket.Status.IN_PROGRESS)
