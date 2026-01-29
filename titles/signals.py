import os

from django.db.models.signals import pre_delete, post_save
from django.dispatch.dispatcher import receiver

from common.utils.files import delete_orphaned_files
from titles.models import Title, Group, Poster, Backdrop


@receiver(pre_delete, sender=Poster)
def poster_delete(sender, instance, **kwargs):
    delete_orphaned_files(*instance.media_files)

@receiver(pre_delete, sender=Backdrop)
def backdrop_delete(sender, instance, **kwargs):
    if instance.backdrop_local:
        delete_orphaned_files(instance.backdrop_local)
