from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from video_player.models import ViewingHistory


@receiver(post_save, sender=ViewingHistory)
@receiver(post_delete, sender=ViewingHistory)
def comments_changed(sender, instance, **kwargs):
    cache.delete_pattern(f'*history:user:{instance.user_id}*')
