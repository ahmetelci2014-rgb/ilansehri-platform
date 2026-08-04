from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class UserType(models.TextChoices):
        INDIVIDUAL = "individual", "Bireysel"
        BUSINESS = "business", "Kurumsal"
        PROVIDER = "provider", "Hizmet Veren"
        PARTNER = "partner", "Görev Ortağı"

    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.INDIVIDUAL)
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=80, blank=True)
    district = models.CharField(max_length=80, blank=True)
    is_phone_verified = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.get_full_name() or self.username
