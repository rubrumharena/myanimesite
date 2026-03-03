from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch.dispatcher import receiver

from common.utils.files import delete_orphaned_files
from users.models import User
from users.tasks import index_user


@receiver(pre_delete, sender=User)
def user_delete(sender, instance, **kwargs):
    delete_orphaned_files([instance.avatar.path if instance.avatar else None])


@receiver(post_save, sender=User)
def user_save(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: index_user.delay(instance.id))
