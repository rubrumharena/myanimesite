from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from common.utils.files import delete_orphaned_files
from lists.models import Collection, Folder
from lists.tasks import invalidate_folders_cache


@receiver(pre_delete, sender=Folder)
def folder_delete(sender, instance, **kwargs):
    if instance.image:
        delete_orphaned_files(instance.image)


@receiver(pre_delete, sender=Collection)
def collection_delete(sender, instance, **kwargs):
    if instance.image:
        delete_orphaned_files(instance.image)


@receiver(m2m_changed, sender=Folder.titles.through)
def folder_titles_changed(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.updated_at = timezone.now()
        instance.save(update_fields=['updated_at'])
        invalidate_folders_cache.delay(instance.id)


@receiver(post_save, sender=Folder)
@receiver(post_delete, sender=Folder)
def folder_changed(sender, instance, **kwargs):
    invalidate_folders_cache.delay(instance.id)
