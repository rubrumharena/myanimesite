from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from comments.models import Comment


@receiver(post_save, sender=Comment)
@receiver(post_delete, sender=Comment)
def comments_changed(sender, instance, **kwargs):
    cache.delete_pattern(f'*comments*title:{instance.title_id}*')
