from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import User


def _delete_avatar(avatar):
    if avatar and getattr(avatar, "name", ""):
        avatar.delete(save=False)


@receiver(pre_save, sender=User)
def delete_replaced_avatar(sender, instance, **kwargs):
    if not instance.pk:
        return
    old = sender.objects.filter(pk=instance.pk).only("avatar").first()
    if old and old.avatar and old.avatar.name != instance.avatar.name:
        _delete_avatar(old.avatar)


@receiver(post_delete, sender=User)
def delete_user_avatar(sender, instance, **kwargs):
    _delete_avatar(instance.avatar)
