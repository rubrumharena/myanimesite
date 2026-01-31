from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver

from common.utils.files import delete_orphaned_files
from users.models import User


@receiver(pre_delete, sender=User)
def user_delete(sender, instance, **kwargs):
    delete_orphaned_files([instance.avatar.path if instance.avatar else None])
