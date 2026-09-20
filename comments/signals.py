from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from comments.models import Comment
from common.utils.cache_keys import delete_pattern


@receiver(post_save, sender=Comment)
@receiver(post_delete, sender=Comment)
def comments_changed(sender, instance, **kwargs):
    delete_pattern(f'*comments*title:{instance.title_id}*')


@receiver(pre_delete, sender=Comment)
def delete_review(sender, instance, **kwargs):
    if instance.review:
        instance.review.delete()
