import uuid
from datetime import timedelta

from celery import shared_task
from django.utils.timezone import now

from accounts.models import EmailVerification


@shared_task
def send_email(user_id: int, email_type: str) -> None:
    record = EmailVerification.objects.create(
        code=uuid.uuid4(),
        user_id=user_id,
        expiration=now() + timedelta(hours=1),
        type=email_type,
    )
    record.send_verification_email()
