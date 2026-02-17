from django.db.models.signals import m2m_changed, pre_delete
from django.dispatch.dispatcher import receiver
from django.utils import timezone

from common.utils.files import delete_orphaned_files
from lists.models import Folder
from titles.models import Backdrop, Poster


@receiver(pre_delete, sender=Poster)
def poster_delete(sender, instance, **kwargs):
    delete_orphaned_files(*instance.media_files)


@receiver(pre_delete, sender=Backdrop)
def backdrop_delete(sender, instance, **kwargs):
    if instance.backdrop_local:
        delete_orphaned_files(instance.backdrop_local)


@receiver(m2m_changed, sender=Folder.titles.through)
def folder_titles_changed(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.updated_at = timezone.now()
        instance.save(update_fields=['updated_at'])
