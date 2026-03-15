from django.core.cache import cache
from django.db.models.signals import m2m_changed, pre_delete
from django.dispatch import receiver
from django.utils import timezone

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


@receiver(m2m_changed, sender=Folder.titles.through)
def folder_titles_changed(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.updated_at = timezone.now()
        instance.save(update_fields=['updated_at'])
        cache.delete_pattern(f'folder:{instance.id}:*')
