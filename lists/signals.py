from django.db.models.signals import pre_delete
from django.dispatch import receiver

from common.utils.files import delete_orphaned_files
from lists.models import Collection, Folder


@receiver(pre_delete, sender=Folder)
def folder_delete(sender, instance, **kwargs):
    if instance.image:
        delete_orphaned_files(instance.image)


@receiver(pre_delete, sender=Collection)
def collection_delete(sender, instance, **kwargs):
    if instance.image:
        delete_orphaned_files(instance.image)
