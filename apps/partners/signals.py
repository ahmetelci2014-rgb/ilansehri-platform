from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Task


def _delete_proof(proof_file):
    if proof_file and getattr(proof_file, "name", ""):
        proof_file.delete(save=False)


@receiver(pre_save, sender=Task)
def delete_replaced_task_proof(sender, instance, **kwargs):
    if not instance.pk:
        return
    old = sender.objects.filter(pk=instance.pk).only("proof_file").first()
    if old and old.proof_file and old.proof_file.name != instance.proof_file.name:
        _delete_proof(old.proof_file)


@receiver(post_delete, sender=Task)
def delete_task_proof(sender, instance, **kwargs):
    _delete_proof(instance.proof_file)
