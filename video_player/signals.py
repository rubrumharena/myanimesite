from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.utils.cache_keys import delete_pattern
from video_player.models import ViewingHistory


@receiver(post_save, sender=ViewingHistory)
@receiver(post_delete, sender=ViewingHistory)
def comments_changed(sender, instance, **kwargs):
    delete_pattern(f'*history:user:{instance.user_id}*')
