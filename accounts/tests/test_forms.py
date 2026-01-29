from django.test import TestCase
from unittest.mock import patch

from accounts.forms import UserRegisterForm, EmailForm, UserLoginForm
from accounts.models import EmailVerification
from lists.models import Folder
from users.models import User


class UserRegisterFormTestCase(TestCase):

    def setUp(self):
        self.test_data = {'username': 'test_user', 'email': 'test@gmail.com', 'password1': '123456test', 'password2': '123456test'}

    @patch('accounts.forms.EmailVerification.send_verification_email')
    def test_happy_path(self, mock_verification_email):
        form = UserRegisterForm(data=self.test_data)
        self.assertTrue(form.is_valid())

        form.save()
        user = User.objects.filter(email=self.test_data['email'])

        self.assertTrue(user.exists())
        self.assertTrue(Folder.objects.filter(name=Folder.FAVORITES, user=user[0]).exists())
        self.assertTrue(EmailVerification.objects.filter(user=user[0]).exists())
        mock_verification_email.assert_called_once()

    def test_if_user_is_not_committed(self):
        form = UserRegisterForm(data=self.test_data)
        self.assertTrue(form.is_valid())

        form.save(commit=False)
        user = User.objects.filter(email=self.test_data['email'])

        self.assertFalse(user.exists())
        self.assertFalse(Folder.objects.filter(name=Folder.FAVORITES, user=user.first()).exists())
        self.assertFalse(EmailVerification.objects.filter(user=user.first()).exists())


class EmailFormTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='test_user', email='test@gmail.com', password='123456')
        self.test_data = {'email': 'test@gmail.com'}

    @patch('accounts.forms.EmailVerification.send_verification_email')
    def test_happy_path(self, mock_verification_email):
        form = EmailForm(data=self.test_data)

        self.assertTrue(form.is_valid())
        self.assertTrue(EmailVerification.objects.filter(user=self.user).exists())
        mock_verification_email.assert_called_once()

    def test_if_user_does_not_exists(self):
        User.objects.all().delete()
        form = EmailForm(data=self.test_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['email'], ['Нет пользователя с таким email.'])


class UserLoginTestCase(TestCase):

    def setUp(self):
        User.objects.create_user(username='test_user', password='123456test', email='test@gmail.com')
        self.test_data = {'username': 'test_user', 'password': '123456test'}

    def test_happy_path(self):
        form = UserLoginForm(data=self.test_data)

        self.assertTrue(form.is_valid())

    def test_if_user_user_uses_email_to_login(self):
        self.test_data['username'] = 'test@gmail.com'
        form = UserLoginForm(data=self.test_data)

        self.assertTrue(form.is_valid())

    def test_if_user_user_uses_email_and_password_is_incorrect_login(self):
        self.test_data['username'] = 'test@gmail.com'
        self.test_data['password'] = '987654321'
        form = UserLoginForm(data=self.test_data)

        self.assertFalse(form.is_valid())
