from django.db.models.signals import pre_delete
from django.dispatch import receiver

from comments.models import Comment

#
# @receiver(post_save, sender=Comment)
# @receiver(post_delete, sender=Comment)
# def comments_changed(sender, instance, **kwargs):
#     cache.delete_pattern(f'*comments*title:{instance.title_id}*')


@receiver(pre_delete, sender=Comment)
def delete_review(sender, instance, **kwargs):
    if instance.review:
        instance.review.delete()
