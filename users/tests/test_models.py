import tempfile
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings

from lists.models import Folder
from users.models import User


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class UserModelMainTestCase(TransactionTestCase):
    def setUp(self):
        self.base_data = {'username': 'test', 'password': '123456', 'email': 'test@gmail.com'}

    def test_email_becomes_none(self):
        self.base_data['email'] = ''
        User.objects.create(**self.base_data)
        self.assertIsNone(User.objects.first().email)

    @patch('users.models.resize_image')
    def test_happy_path(self, mock_resize_image):
        user = User.objects.create(**self.base_data)
        self.assertTrue(Folder.objects.filter(user=user, type=Folder.SYSTEM).exists())
        mock_resize_image.assert_called_once()

    @patch('users.signals.index_user.delay')
    def test_user_gets_indexed_on_create(self, mock_delay):
        user = User.objects.create(username='test')

        self.assertTrue(mock_delay.called)
        mock_delay.assert_called_once_with(user.id)
