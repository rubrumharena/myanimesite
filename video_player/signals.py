


# @receiver(post_save, sender=ViewingHistory)
# @receiver(post_delete, sender=ViewingHistory)
# def comments_changed(sender, instance, **kwargs):
#     cache.delete_pattern(f'*history:user:{instance.user_id}*')
