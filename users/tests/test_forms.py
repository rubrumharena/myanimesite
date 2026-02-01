import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings

from accounts.models import EmailVerification
from common.utils.testing_components import create_image
from users.forms import (AvatarUpdateForm, EmailUpdateForm, PasswordUpdateForm,
                         ProfileUpdateForm)
from users.models import User


class ProfileUpdateFormTestCase(TestCase):
    def setUp(self):
        self.username = 'test_username'
        self.password = '<PASSWORD>'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_form_updates_fields(self):
        self.client.login(username=self.username, password=self.password)
        data_before = {'username': self.username, 'bio': None, 'name': None}
        data_after = {'username': 'new_username', 'bio': 'test_bio', 'name': 'test_name'}

        for key, value in data_before.items():
            self.assertEqual(getattr(self.user, key), value)

        ProfileUpdateForm(data=data_after, instance=self.user).save()

        updated_user = User.objects.get(username='new_username')
        self.assertFalse(User.objects.filter(username=self.username).exists())
        for key, value in data_after.items():
            self.assertEqual(getattr(updated_user, key), value)


class PasswordUpdateFormTestCase(TestCase):
    def setUp(self):
        self.username = 'test_username'
        self.password = '12345'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_password_is_changed(self):
        old_hash = self.user.password

        data = {'old_password': self.password, 'new_password1': 'test87654321', 'new_password2': 'test87654321'}
        form = PasswordUpdateForm(data=data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        self.assertNotEqual(self.user.password, old_hash)
        self.assertFalse(self.user.check_password(self.password))

    def test_old_password_is_invalid(self):
        data = {'old_password': 'test', 'new_password1': 'test87654321', 'new_password2': 'test87654321'}
        form = PasswordUpdateForm(data=data, user=self.user)

        self.assertFalse(form.is_valid(), form.errors)
        self.assertTrue(self.user.check_password(self.password))

    def test_new_password_is_invalid(self):
        data = {'old_password': 'test', 'new_password1': 'test87654321test', 'new_password2': 'test87654321'}
        form = PasswordUpdateForm(data=data, user=self.user)

        self.assertFalse(form.is_valid(), form.errors)
        self.assertTrue(self.user.check_password(self.password))


class EmailUpdateFormTestCase(TestCase):
    def setUp(self):
        self.username = 'test_username'
        self.password = '12345'
        self.user = User.objects.create_user(username=self.username, password=self.password, email='email@gmail.com')

        self.test_data = {'email': 'test@gmail.com'}

    @patch('accounts.forms.EmailVerification.send_verification_email')
    def test_happy_path(self, mock_verification_email):
        prev_email = self.user.email

        form = EmailUpdateForm(data=self.test_data, instance=self.user)
        self.assertTrue(form.is_valid())

        form.save()

        updated_user = User.objects.get(username=self.username)

        self.assertTrue(EmailVerification.objects.filter(user=self.user).exists())
        self.assertNotEqual(prev_email, updated_user.email)
        mock_verification_email.assert_called_once()

    @patch('accounts.forms.EmailVerification.send_verification_email')
    def test_invalid_cases(self, mock_verification_email):
        User.objects.create_user(username='new_username', password='<PASSWORD>', **self.test_data)

        prev_email = self.user.email
        test_cases = [self.test_data, {'email': prev_email}]
        error_messages = [['Пользователь с таким email уже существует.'], ['Новый email не отличается от предыдущего.']]

        for case, message in zip(test_cases, error_messages):
            with self.subTest(case=case):
                form = EmailUpdateForm(data=case, instance=self.user)
                updated_user = User.objects.get(username=self.username)

                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors, {'email': message})
                self.assertFalse(EmailVerification.objects.filter(user=self.user).exists())
                self.assertEqual(prev_email, updated_user.email)
                mock_verification_email.assert_not_called()


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class AvatarUpdateTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='123456')

    def test_happy_path(self):
        avatar = create_image('test')
        form = AvatarUpdateForm(data={'avatar': avatar}, files={'avatar': avatar}, instance=self.user)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(User.objects.get(username='test').avatar)

    def test_form_invalid(self):
        test_cases = [create_image('test1', (1, 1)), create_image('test2', mb=1000)]
        for case in test_cases:
            with self.subTest(case=case):
                form = AvatarUpdateForm(data={'avatar': case}, files={'avatar': case}, instance=self.user)
                self.assertFalse(form.is_valid())
