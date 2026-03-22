from http import HTTPStatus
from unittest.mock import patch

from django.shortcuts import reverse
from django.test import TestCase
from django.utils import timezone

from subscriptions.forms import SubscriptionForm
from subscriptions.models import Subscription, UserSubscription
from users.models import User


class SubscriptionTemplateViewTestCase(TestCase):
    def setUp(self):
        self.price_list = [5, 20, 35]
        self.plans = [1, 6, 12]
        subscriptions = [
            Subscription(name=f'Sub {i}', price=price, plan=plan, stripe_price_id=i)
            for i, price, plan in zip(range(3), self.price_list, self.plans)
        ]
        Subscription.objects.bulk_create(subscriptions)

    def test_happy_path(self):
        response = self.client.get(reverse('subscriptions:issue_order'))
        context = response.context

        expected_data = [
            (
                round(100 - ((price * 100) / (self.price_list[0] * plan))),
                round(price / plan, 2),
            )
            for price, plan in zip(self.price_list, self.plans)
        ]

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsInstance(context['form'], SubscriptionForm)

        plans = list(context['plans'])

        self.assertEqual(len(plans), len(expected_data))

        for i, expected in enumerate(expected_data):
            expected_economy, expected_real_price = expected

            with self.subTest(
                economy=expected_economy,
                real_price=expected_real_price,
            ):
                cur_plan = plans[i][0]
                self.assertEqual(int(cur_plan.economy), expected_economy)
                self.assertEqual(float(cur_plan.real_price), expected_real_price)

    def test_when_no_any_plan(self):
        Subscription.objects.all().delete()

        response = self.client.get(reverse('subscriptions:issue_order'))
        context = response.context

        self.assertIsNone(context.get('form'))
        self.assertIsNone(context.get('plans'))


class SubscriptionActivatedTemplateViewTestCase(TestCase):
    def setUp(self):
        self.username = 'test'
        self.password = '12345'
        self.user = User.objects.create_user(username=self.username, password=self.password, is_premium=True)
        self.path = reverse('subscriptions:activated')

        sub = Subscription.objects.create(name='sub', price=10, plan=1, stripe_price_id=1)
        self.user_sub = UserSubscription.objects.create(
            user=self.user,
            subscription=sub,
            stripe_subscription_id=1,
            status=UserSubscription.ACTIVE,
            ends_at=timezone.now(),
        )

    def test_raises_404_when_user_is_not_premium(self):
        user = User.objects.create_user(username='new_test', password=self.password)
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch('subscriptions.views.format_subscription_period', return_value='test')
    def test_happy_path(self, mock_format_subscription_period_mock):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['ends_at'], 'test')
        mock_format_subscription_period_mock.assert_called_once_with(self.user_sub.ends_at)
