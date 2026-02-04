import uuid
from datetime import timedelta
from http import HTTPStatus
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.shortcuts import reverse
from django.test import TestCase
from django.utils.timezone import now

from accounts.forms import EmailForm, PasswordResetForm, UserLoginForm, UserRegisterForm
from accounts.models import EmailVerification
from users.models import User


class RegistrationViewTestCase(TestCase):
    def setUp(self):
        self.path = reverse('accounts:register')
        self.data = {
            'username': 'test_user',
            'email': 'test@gmail.com',
            'password1': 'test12345',
            'password2': 'test12345',
        }

    def test_view_get(self):
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], 'Регистрация | MYANIMESITE')
        self.assertIsInstance(context['form'], UserRegisterForm)

    def test_view_post_happy_path(self):
        response = self.client.post(self.path, self.data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_view_post_if_form_invalid(self):
        self.data['password1'] = '<PASSWORD>'
        response = self.client.post(self.path, self.data)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsInstance(context['form'], UserRegisterForm)
        self.assertContains(response, 'error')


class UserLoginViewTestCase(TestCase):
    def setUp(self):
        User.objects.create_user(username='test_user', password='123456test', email='test@gmail.com')
        self.test_data = {'username': 'test_user', 'password': '123456test'}
        self.path = reverse('accounts:login')

    def test_view_get(self):
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], 'Авторизация | MYANIMESITE')
        self.assertIsInstance(context['form'], UserLoginForm)

    def test_view_post_happy_path(self):
        response = self.client.post(self.path, self.test_data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_view_post_when_user_login_with_email(self):
        self.test_data['username'] = 'test@gmail.com'
        response = self.client.post(self.path, self.test_data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_view_post_if_form_invalid(self):
        self.test_data['username'] = 'tst@gmail.com'
        response = self.client.post(self.path, self.test_data)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsInstance(context['form'], UserLoginForm)
        self.assertContains(response, 'error')


class RecoveryViewTestCase(TestCase):
    def setUp(self):
        User.objects.create_user(username='test_user', password='123456test', email='test@gmail.com')
        EmailVerification.objects.all().delete()
        self.path = reverse('accounts:recovery')

    def test_view_get(self):
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], 'Восстановление пароля | MYANIMESITE')
        self.assertIsInstance(context['form'], EmailForm)

    def test_view_post_happy_path(self):
        response = self.client.post(self.path, {'email': 'test@gmail.com'})

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(list(get_messages(response.wsgi_request)))
        self.assertEqual(EmailVerification.objects.all().count(), 1)

    def test_view_post_if_email_is_invalid(self):
        response = self.client.post(self.path, {'email': 'tst@gmail.com'})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(list(get_messages(response.wsgi_request)))


class EmailVerificationViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_user', password='123456test', email='test@gmail.com')
        EmailVerification.objects.all().delete()
        self.code = uuid.uuid4()
        EmailVerification.objects.create(
            user=self.user, code=self.code, type=EmailVerification.VERIFY_EMAIL, expiration=now() + timedelta(hours=1)
        )
        self.path = reverse('accounts:account_verification', kwargs={'code': self.code, 'user_id': self.user.id})

    def test_happy_path(self):
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], 'Верификация аккаунта | MYANIMESITE')
        self.assertTrue(EmailVerification.objects.first().used)
        self.assertTrue(User.objects.first().is_verified)

    def test_if_invalid_url(self):
        response = self.client.get(reverse('accounts:account_verification', kwargs={'code': self.code, 'user_id': 999}))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch('accounts.views.EmailVerification.is_expired', return_value=True)
    def test_if_url_expired(self, is_expired):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)


class VerificationMessageViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_user', password='123456test', email='test@gmail.com')
        self.reset_code = uuid.uuid4()
        self.verify_code = uuid.uuid4()

        EmailVerification.objects.create(
            user=self.user,
            code=self.verify_code,
            type=EmailVerification.VERIFY_EMAIL,
            expiration=now() + timedelta(hours=1),
            used=True,
        )
        EmailVerification.objects.create(
            user=self.user,
            code=self.reset_code,
            type=EmailVerification.RESET_PASSWORD,
            expiration=now() + timedelta(hours=1),
        )

        self.expired_kwargs = {'code': '', 'user_id': self.user.id, 'status': 'expired'}
        self.used_kwargs = {'code': '', 'user_id': self.user.id, 'status': 'used'}

    def _common_tests(self, response, expected_type, expected_status):
        context = response.context
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], 'Сообщение о верификации | MYANIMESITE')
        self.assertEqual(context['type'], expected_type)
        self.assertEqual(context['status'], expected_status)

    def test_happy_path_used(self):
        self.used_kwargs['code'] = self.verify_code
        path = reverse('accounts:verification_message', kwargs=self.used_kwargs)
        response = self.client.get(path)
        self._common_tests(response, EmailVerification.VERIFY_EMAIL, EmailVerification.USED)

    @patch('accounts.views.EmailVerification.is_expired', return_value=True)
    def test_happy_path_expired(self, is_expired):
        self.expired_kwargs['code'] = self.reset_code
        path = reverse('accounts:verification_message', kwargs=self.expired_kwargs)
        response = self.client.get(path)
        self._common_tests(response, EmailVerification.RESET_PASSWORD, EmailVerification.EXPIRED)

    def test_raising_of_404(self):
        verify_record = EmailVerification.objects.get(code=self.verify_code)
        verify_record.used = False
        verify_record.save()

        self.used_kwargs['code'] = self.verify_code
        self.expired_kwargs['code'] = self.reset_code
        invalid_kwargs = self.expired_kwargs
        invalid_kwargs['status'] = 'test'
        paths = [
            reverse('accounts:verification_message', kwargs=self.used_kwargs),
            reverse('accounts:verification_message', kwargs=self.expired_kwargs),
            reverse('accounts:verification_message', kwargs=invalid_kwargs),
        ]

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class PasswordResetViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_user', password='123456test', email='test@gmail.com')
        self.code = uuid.uuid4()
        EmailVerification.objects.create(
            user=self.user, code=self.code, type=EmailVerification.RESET_PASSWORD, expiration=now() + timedelta(hours=1)
        )
        self.path = reverse('accounts:password_reset', kwargs={'code': self.code, 'user_id': self.user.id})

    def test_view_get(self):
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], 'Сброс пароля | MYANIMESITE')
        self.assertIsInstance(context['form'], PasswordResetForm)

    def test_view_get_if_invalid_user(self):
        self.path = reverse('accounts:password_reset', kwargs={'code': self.code, 'user_id': 999})
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch('accounts.views.EmailVerification.is_expired', return_value=True)
    def test_view_get_if_url_expired(self, is_expired):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_view_post(self):
        data = {'new_password1': 'newtest123456', 'new_password2': 'newtest123456'}
        response = self.client.post(self.path, data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(EmailVerification.objects.get(code=self.code, user=self.user).used)

    def test_view_post_invalid(self):
        data = {'new_password1': 'newtest123456789', 'new_password2': 'newtest123456'}
        response = self.client.post(self.path, data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(EmailVerification.objects.get(code=self.code, user=self.user).used)
        self.assertContains(response, 'error')


class DeleteAccountTestView(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_user', password='123456test', email='test@gmail.com')

        self.path = reverse('accounts:delete_account')

    def test_happy_path(self):
        self.client.login(username='test_user', password='123456test')
        self.client.post(self.path)

        self.assertEqual(User.objects.all().count(), 0)

    def test_anonymous_user(self):
        response = self.client.post(self.path)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
