from http import HTTPStatus

from django.shortcuts import reverse
from django.test import TestCase

from subscriptions.forms import SubscriptionForm
from subscriptions.models import Subscription


class SubscriptionTemplateViewTestCase(TestCase):

    def setUp(self):
        self.price_list = [5, 20, 35]
        self.plans = [1, 6, 12]
        subscriptions = [Subscription(name=f'Sub {i}', price=price, plan=plan, stripe_price_id=i)
                         for i, price, plan in zip(range(3), self.price_list, self.plans)]
        Subscription.objects.bulk_create(subscriptions)

    def test_queryset_hangs_to_field_manually(self):
        subscriptions = Subscription.objects.order_by('plan')
        form = SubscriptionForm(subscriptions_qs=subscriptions)
        self.assertEqual(len(form['subscription']), subscriptions.count())
        self.assertEqual(form['subscription'].initial, subscriptions.first())

    def test_queryset_hangs_to_field_automatically(self):
        subscriptions = Subscription.objects.order_by('plan')
        form = SubscriptionForm()
        self.assertEqual(len(form['subscription']), subscriptions.count())
        self.assertEqual(form['subscription'].initial, subscriptions.first())
