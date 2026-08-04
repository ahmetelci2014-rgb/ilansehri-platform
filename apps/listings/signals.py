from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import ListingImage, Message


def _delete_file(field_file):
    if field_file and getattr(field_file, "name", ""):
        field_file.delete(save=False)


@receiver(post_delete, sender=ListingImage)
def delete_listing_image_file(sender, instance, **kwargs):
    _delete_file(instance.image)


@receiver(post_delete, sender=Message)
def delete_message_attachment(sender, instance, **kwargs):
    _delete_file(instance.attachment)


@receiver(pre_save, sender=ListingImage)
def replace_listing_image_file(sender, instance, **kwargs):
    if not instance.pk:
        return
    old = sender.objects.filter(pk=instance.pk).only("image").first()
    if old and old.image and old.image.name != instance.image.name:
        _delete_file(old.image)


@receiver(pre_save, sender=Message)
def replace_message_attachment(sender, instance, **kwargs):
    if not instance.pk:
        return
    old = sender.objects.filter(pk=instance.pk).only("attachment").first()
    if old and old.attachment and old.attachment.name != instance.attachment.name:
        _delete_file(old.attachment)
