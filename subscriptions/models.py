from django.db import models

from users.models import User

# Create your models here.


class Subscription(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)
    name = models.CharField(max_length=20)
    plan = models.SmallIntegerField()
    stripe_price_id = models.CharField(max_length=30)


class UserSubscription(models.Model):
    ACTIVE = 'active'
    PAST_DUE = 'past_due'
    CANCELLED = 'cancelled'
    UNPAID = 'unpaid'
    STATUS_CHOICES = ((ACTIVE, 'Активная'), (PAST_DUE, 'Просрочена'), (UNPAID, 'Неоплачена'), (CANCELLED, 'Отменена'))

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=UNPAID)
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
