from celery import shared_task
from django.conf import settings

from users.documents import UserDocument
from users.models import User


@shared_task
def index_user(user_id):
    if not settings.ELASTICSEARCH_ENABLED:
        return
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return
    UserDocument().update(user)
