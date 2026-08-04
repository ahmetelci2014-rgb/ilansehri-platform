from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.accounts.models import User, UserFollow
from apps.listings.models import Category, Listing, ListingPriceHistory, Notification, Offer, OfferEvent
from apps.managed_services.models import ManagedActivity, ManagedRequest
from apps.partners.models import PartnerProfile, Task
from apps.support_center.models import SupportReply, SupportTicket


class Command(BaseCommand):
    help = "Geliştirme ve sunum ortamı için örnek İlan Şehri verileri oluşturur."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Önce demo kullanıcılarının ilanlarını siler.")
        parser.add_argument("--with-admin", action="store_true", help="Yalnız geliştirme için demo yönetici oluşturur.")

    def handle(self, *args, **options):
        if options["reset"]:
            User.objects.filter(username__startswith="demo_").delete()

        seller, _ = User.objects.get_or_create(
            username="demo_satici",
            defaults={
                "first_name": "Mehmet",
                "last_name": "Demir",
                "email": "satici@demo.local",
                "phone": "05550000011",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "is_phone_verified": True,
                "verification_level": User.VerificationLevel.PHONE,
            },
        )
        seller.set_password("Demo1234!")
        seller.save()
        buyer, _ = User.objects.get_or_create(
            username="demo_alici",
            defaults={
                "first_name": "Ayşe",
                "last_name": "Kaya",
                "email": "alici@demo.local",
                "phone": "05550000012",
                "city": "Şanlıurfa",
                "district": "Haliliye",
                "is_phone_verified": True,
                "verification_level": User.VerificationLevel.PHONE,
            },
        )
        buyer.set_password("Demo1234!")
        buyer.save()
        partner_user, _ = User.objects.get_or_create(
            username="demo_partner",
            defaults={
                "first_name": "Hasan",
                "last_name": "Yıldız",
                "email": "partner@demo.local",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "user_type": User.UserType.PARTNER,
            },
        )
        partner_user.set_password("Demo1234!")
        partner_user.save()

        if options["with_admin"]:
            admin, _ = User.objects.get_or_create(
                username="demo_admin",
                defaults={"first_name": "Demo", "last_name": "Yönetici", "email": "admin@demo.local"},
            )
            admin.is_staff = True
            admin.is_superuser = True
            admin.is_active = True
            admin.set_password("DemoAdmin1234!")
            admin.save()

        categories = {item.name: item for item in Category.objects.filter(parent__isnull=False)}
        fallback = Category.objects.filter(is_active=True).first()
        samples = [
            {
                "key": "demo-telefon",
                "category": categories.get("Elektronik", fallback),
                "kind": Listing.Kind.PRODUCT,
                "action": Listing.Action.SELL,
                "title": "Kutulu ve garantili akıllı telefon",
                "description": "Az kullanılmış, kutusu ve faturası mevcut. Elden teslim önceliklidir.",
                "price": Decimal("28500"),
                "condition": "Az kullanılmış",
                "brand": "Apple",
                "model_name": "iPhone 15",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "neighborhood": "Atakent",
            },
            {
                "key": "demo-arac",
                "category": categories.get("Otomobil", fallback),
                "kind": Listing.Kind.VEHICLE,
                "action": Listing.Action.SELL,
                "title": "2022 model düşük kilometre otomobil",
                "description": "Bakımları zamanında yapılmış, aile aracı. Ekspertiz raporu görüşmede paylaşılır.",
                "price": Decimal("985000"),
                "condition": "Hasarsız",
                "brand": "Toyota",
                "model_name": "Corolla",
                "model_year": 2022,
                "mileage": 42000,
                "fuel_type": Listing.FuelType.GASOLINE,
                "transmission": Listing.Transmission.AUTOMATIC,
                "city": "Şanlıurfa",
                "district": "Haliliye",
                "neighborhood": "Sırrın",
            },
            {
                "key": "demo-emlak",
                "category": categories.get("Konut", fallback),
                "kind": Listing.Kind.REAL_ESTATE,
                "action": Listing.Action.RENT,
                "management_mode": Listing.ManagementMode.FULL,
                "title": "Karaköprü'de ferah 3+1 kiralık daire",
                "description": "Aileye uygun, ulaşımı kolay, doğalgazlı ve bakımlı daire. Süreç İlan Şehri tarafından yönetilmektedir.",
                "price": Decimal("22000"),
                "room_count": "3+1",
                "area_m2": 165,
                "building_age": 4,
                "floor_location": "5. kat",
                "heating_type": "Doğalgaz kombi",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "neighborhood": "Akpıyar",
            },
            {
                "key": "demo-hizmet",
                "category": categories.get("Tamir & Tadilat", fallback),
                "kind": Listing.Kind.SERVICE,
                "action": Listing.Action.SERVICE_OFFER,
                "title": "Ev ve işyeri elektrik tesisatı hizmeti",
                "description": "Arıza, tesisat yenileme ve aydınlatma montajı. İş öncesi ücretsiz keşif.",
                "price_on_request": True,
                "service_area": "Karaköprü ve Haliliye",
                "fee_type": Listing.FeeType.NEGOTIABLE,
                "city": "Şanlıurfa",
                "district": "Karaköprü",
            },
        ]
        created_listings = []
        for sample in samples:
            key = sample.pop("key")
            listing, _ = Listing.objects.update_or_create(
                slug=key,
                defaults={
                    "owner": seller,
                    "status": Listing.Status.PUBLISHED,
                    **sample,
                },
            )
            created_listings.append(listing)

        managed_listing = next(item for item in created_listings if item.management_mode == Listing.ManagementMode.FULL)
        managed, _ = ManagedRequest.objects.get_or_create(
            listing=managed_listing,
            defaults={
                "customer": seller,
                "package": ManagedRequest.Package.FULL,
                "status": ManagedRequest.Status.ACTIVE,
                "progress": 35,
                "next_action": "Profesyonel fotoğraf çekimi",
            },
        )
        ManagedActivity.objects.get_or_create(
            managed_request=managed,
            note="İhtiyaç analizi tamamlandı ve fotoğraf görevi planlandı.",
            defaults={"activity_type": ManagedActivity.ActivityType.STATUS},
        )
        partner, _ = PartnerProfile.objects.get_or_create(
            user=partner_user,
            defaults={
                "status": PartnerProfile.Status.ACTIVE,
                "level": PartnerProfile.Level.VERIFIED,
                "skills": ["photo", "listing"],
                "service_cities": ["Şanlıurfa"],
                "identity_verified": True,
            },
        )
        Task.objects.get_or_create(
            managed_request=managed,
            title="Kiralık daire fotoğraf çekimi",
            defaults={
                "task_type": Task.TaskType.PHOTO,
                "description": "Yatay ve dikey formatta en az 12 aydınlık fotoğraf çek.",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "reward": Decimal("650"),
                "success_bonus": Decimal("100"),
            },
        )
        phone_listing = created_listings[0]
        offer, _ = Offer.objects.get_or_create(
            listing=phone_listing,
            sender=buyer,
            defaults={
                "amount": Decimal("27000"),
                "message": "Bugün elden teslim alabilirim.",
                "last_actor": buyer,
            },
        )
        if offer.last_actor_id is None:
            offer.last_actor = buyer
            offer.save(update_fields=["last_actor", "updated_at"])
        OfferEvent.objects.get_or_create(
            offer=offer,
            event_type=OfferEvent.Type.SUBMITTED,
            defaults={
                "actor": buyer,
                "amount": offer.amount,
                "message": offer.message,
            },
        )
        UserFollow.objects.get_or_create(follower=buyer, seller=seller)
        ListingPriceHistory.objects.get_or_create(
            listing=phone_listing,
            old_price=Decimal("30000"),
            new_price=Decimal("28500"),
            defaults={"changed_by": seller},
        )
        Notification.objects.get_or_create(
            user=seller,
            listing=phone_listing,
            notification_type=Notification.Type.OFFER,
            title="Demo teklif bildirimi",
            defaults={"actor": buyer, "body": offer.message, "link": "/hesap/hesabim/#teklifler"},
        )

        demo_ticket, _ = SupportTicket.objects.get_or_create(
            user=buyer,
            subject="Teklif kabul edilince ne yapmalıyım?",
            defaults={
                "category": SupportTicket.Category.TRANSACTION,
                "priority": SupportTicket.Priority.NORMAL,
                "status": SupportTicket.Status.WAITING_USER if options["with_admin"] else SupportTicket.Status.OPEN,
                "description": "Gönderdiğim teklif kabul edilirse teslim ve işlem adımlarını nereden takip edeceğimi öğrenmek istiyorum.",
                "related_listing": phone_listing,
            },
        )
        if options["with_admin"]:
            demo_ticket.assigned_to = admin
            demo_ticket.status = SupportTicket.Status.WAITING_USER
            demo_ticket.save(update_fields=["assigned_to", "status", "updated_at"])
            SupportReply.objects.get_or_create(
                ticket=demo_ticket,
                author=admin,
                is_internal_note=False,
                defaults={
                    "message": "Teklif kabul edildiğinde Teklif Merkezi'nde işlem kaydı oluşur. Teslim adımlarını bu kayıt üzerinden takip edebilirsin."
                },
            )
        message = "Demo kullanıcılar, ilanlar, destek talepleri, tam yönetim ve görev verileri hazırlandı."
        if options["with_admin"]:
            message += " Demo yönetici: demo_admin / DemoAdmin1234!"
        self.stdout.write(self.style.SUCCESS(message))
