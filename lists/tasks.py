from celery import shared_task
from django.core.cache import cache

from lists.models import Folder


@shared_task
def invalidate_folders_cache(folder_id: int) -> None:
    folder = Folder.objects.get(id=folder_id)
    cache.delete_pattern(f'*folder:{folder.id}:*')
    cache.delete_pattern(f'*profile:{folder.user.id}:*:folders')
