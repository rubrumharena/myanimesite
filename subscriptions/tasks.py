from celery import shared_task

from subscriptions.models import UserSubscription


@shared_task
def send_subscription_email(user_id: int) -> None:
    UserSubscription.objects.get(user_id=user_id).send_email()