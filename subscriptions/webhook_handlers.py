from datetime import datetime, timezone

import stripe

from subscriptions.models import UserSubscription
from subscriptions.tasks import send_subscription_email
from users.models import User


def fulfill_subscription(sub_id: int | str) -> None:
    if not sub_id:
        return

    stripe_sub = stripe.Subscription.retrieve(sub_id)
    meta = stripe_sub.get('metadata', {})

    item = stripe_sub['items']['data'][0]
    period_end = item['current_period_end']
    ends_at = datetime.fromtimestamp(period_end, tz=timezone.utc)

    UserSubscription.objects.update_or_create(
        user_id=meta['user_id'],
        defaults={
            'subscription_id': meta['subscription_id'],
            'ends_at': ends_at,
            'status': UserSubscription.ACTIVE,
            'stripe_subscription_id': sub_id,
        },
    )
    User.objects.filter(id=meta['user_id']).update(is_premium=True)
    send_subscription_email.delay(meta['user_id'])


def handle_payment_failed(sub_id: int | str) -> None:
    cancel_subscription(sub_id, UserSubscription.PAST_DUE)


def handle_subscription_canceled(sub_id: int | str) -> None:
    cancel_subscription(sub_id, UserSubscription.CANCELLED)


def cancel_subscription(sub_id: int | str, status: str) -> None:
    if not sub_id:
        return

    stripe_sub = stripe.Subscription.retrieve(sub_id)
    meta = stripe_sub.get('metadata', {})

    UserSubscription.objects.update_or_create(
        user_id=meta['user_id'],
        defaults={'subscription_id': meta['subscription_id'], 'ends_at': None, 'status': status},
    )
    User.objects.filter(id=meta['user_id']).update(is_premium=False)
    send_subscription_email.delay(meta['user_id'])
