from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.listings.models import Category, Listing
from apps.managed_services.models import ManagedRequest

from .models import PartnerEarning, PartnerProfile, Task, TaskApplication


class PartnerNetworkTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="customerpartner", password="StrongPass_2026")
        self.partner_user = User.objects.create_user(username="partner", password="StrongPass_2026")
        self.staff = User.objects.create_user(username="staffpartner", password="StrongPass_2026", is_staff=True)
        self.profile = PartnerProfile.objects.create(
            user=self.partner_user,
            status=PartnerProfile.Status.ACTIVE,
            service_cities=["Şanlıurfa"],
            skills=["photo"],
        )
        category = Category.objects.create(name="Araç", slug="arac-task")
        listing = Listing.objects.create(
            owner=self.customer, category=category, kind=Listing.Kind.VEHICLE,
            action=Listing.Action.SELL, title="Görev ilanı", description="Açıklama",
            brand="Toyota", model_name="Corolla", model_year=2020,
            city="Şanlıurfa", district="Karaköprü",
        )
        managed = ManagedRequest.objects.create(listing=listing, customer=self.customer)
        self.task = Task.objects.create(
            managed_request=managed,
            title="Araç fotoğraflarını çek",
            task_type=Task.TaskType.PHOTO,
            description="10 profesyonel fotoğraf çek.",
            city="Şanlıurfa",
            district="Karaköprü",
            reward="500",
        )

    def test_partner_applies_and_staff_assigns(self):
        self.client.force_login(self.partner_user)
        self.client.post(reverse("partners:apply_task", kwargs={"pk": self.task.pk}), {"note": "Bugün yapabilirim."})
        application = TaskApplication.objects.get(task=self.task, partner=self.profile)
        self.client.force_login(self.staff)
        self.client.post(
            reverse("partners:task_action", kwargs={"pk": self.task.pk, "action": "accept_application"}),
            {"application_id": application.pk},
        )
        self.task.refresh_from_db(); application.refresh_from_db()
        self.assertEqual(self.task.assigned_partner, self.profile)
        self.assertEqual(application.status, TaskApplication.Status.ACCEPTED)

    def test_completed_task_creates_earning(self):
        self.task.assigned_partner = self.profile
        self.task.status = Task.Status.REVIEW
        self.task.save()
        self.client.force_login(self.staff)
        self.client.post(reverse("partners:task_action", kwargs={"pk": self.task.pk, "action": "complete"}))
        self.task.refresh_from_db(); self.profile.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        self.assertTrue(PartnerEarning.objects.filter(task=self.task).exists())
        self.assertEqual(self.profile.completed_tasks, 1)


    def test_staff_can_approve_partner_profile(self):
        self.profile.status = PartnerProfile.Status.PENDING
        self.profile.save(update_fields=["status"])
        self.client.force_login(self.staff)
        self.client.post(
            reverse("partners:profile_action", kwargs={"pk": self.profile.pk, "action": "approve"})
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, PartnerProfile.Status.ACTIVE)

    def test_staff_can_create_task_for_managed_request(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("partners:task_create", kwargs={"managed_request_id": self.task.managed_request_id}),
            {
                "title": "Fiyat araştırması",
                "task_type": Task.TaskType.PRICE_RESEARCH,
                "description": "Bölgedeki benzer araç fiyatlarını karşılaştır.",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "min_level": PartnerProfile.Level.STARTER,
                "reward": "300.00",
                "success_bonus": "50.00",
            },
        )
        created = Task.objects.get(title="Fiyat araştırması")
        self.assertRedirects(response, reverse("partners:task_detail", kwargs={"pk": created.pk}))
