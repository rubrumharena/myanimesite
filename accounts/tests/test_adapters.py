from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory
from unittest.mock import MagicMock
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from accounts.adapters import SocialAccountAdapter
from users.models import User


class SocialAccountAdapterTestCase(TestCase):
    def setUp(self):
        self.request = RequestFactory().get('/')
        self.adapter = SocialAccountAdapter()
        self.user = User.objects.create_user(
            username='taras',
            email='test@gmail.com',
            password='pass1234'
        )

        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            verified=True,
            primary=True
        )

    def test_existing_email_links_social_account(self):
        social_login = MagicMock()
        social_login.account.extra_data = {'email': 'test@gmail.com'}
        social_login.is_existing = False

        self.adapter.pre_social_login(self.request, social_login)
        social_login.connect.assert_called_once_with(self.request, self.user)

    def test_if_sociallogin_exists(self):
        social_login = MagicMock()
        social_login.is_existing = True

        output = self.adapter.pre_social_login(self.request, social_login)
        self.assertEqual(output, None)

    def test_if_no_email_in_extra_data(self):
        social_login = MagicMock()
        social_login.is_existing = False

        test_cases = [{'email': None}, {}]

        for case in test_cases:
            with self.subTest(case=case):
                social_login.account.extra_data = case
                output = self.adapter.pre_social_login(self.request, social_login)
                self.assertEqual(output, None)

    def test_if_user_logins_first_time(self):
        EmailAddress.objects.all().delete()
        User.objects.all().delete()

        social_login = MagicMock()
        social_login.account.extra_data = {'email': 'test@gmail.com'}
        social_login.is_existing = False

        output = self.adapter.pre_social_login(self.request, social_login)
        self.assertEqual(output, None)
