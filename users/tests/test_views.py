import os
import tempfile
from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.contrib.messages import get_messages
from django.shortcuts import reverse
from django.test import RequestFactory, TestCase, override_settings

from common.utils.testing_components import create_image
from lists.models import Folder
from titles.models import Title
from users.models import Follow, User
from users.views import AccountSettingsView, ProfileSettingsView


class ProfileViewTestCase(TestCase):
    def setUp(self):
        self.username = 'test_user'
        self.password = '123456'
        self.path = reverse('users:profile', kwargs={'username': self.username})
        self.user = User.objects.create_user(username=self.username, email='test@gmaol.com', password=self.password)

        folders = [Folder(name=f'Folder {i}', user=self.user) for i in range(1, 4)]
        titles = [Title(name=f'Title {i}', type=Title.MOVIE) for i in range(1, 4)]

        Folder.objects.bulk_create(folders)
        Title.objects.bulk_create(titles)

        for folder in Folder.objects.all():
            folder.titles.add(*titles)

    def test_happy_path(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], f'{self.username} (@{self.username}) | MYANIMESITE')
        self.assertEqual(list(context['folders'].order_by('id')), list(Folder.objects.order_by('id')))

    def test_if_user_has_hidden_folders(self):
        new_user = User.objects.create_user(username='new_user', email='new_test@gmail.com', password=self.password)
        Folder.objects.create(name='Folder 1', user=new_user, is_hidden=True)
        Folder.objects.create(name='Folder 2', user=new_user)

        self.client.login(username=self.username, password=self.password)
        self.path = reverse('users:profile', kwargs={'username': new_user.username})
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], f'{new_user.username} (@{new_user.username}) | MYANIMESITE')
        self.assertEqual(list(context['folders']), list(Folder.objects.filter(is_hidden=False, user=new_user)))

    def test_if_user_is_anonymous(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], f'{self.username} (@{self.username}) | MYANIMESITE')
        self.assertEqual(list(context['folders'].order_by('id')), list(Folder.objects.order_by('id')))


class FollowersListViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.username = 'test_user'
        cls.password = '123456'
        cls.path = reverse('users:followers', kwargs={'username': cls.username})
        cls.user = User.objects.create_user(username=cls.username, email='test@gmail.com', password=cls.password)
        hashed_password = make_password(cls.password)
        users = [
            User(
                username=f'test_user{i}',
                email=f'test{i}@gmail.com',
                password=hashed_password,
            )
            for i in range(100, 150)
        ]
        User.objects.bulk_create(users)
        followers = [Follow(user=user, following=cls.user) for user in users]

        Follow.objects.bulk_create(followers)

    def test_happy_path(self):
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            context['page_title'], f'Подписчики пользователя {self.username} (@{self.username}) | MYANIMESITE'
        )
        self.assertEqual(
            list(context['object_list']),
            [follow_obj.user for follow_obj in Follow.objects.all().order_by('created_at')[:24]],
        )

    def test_pagination(self):
        response = self.client.get(self.path + '?page=2')
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            context['page_title'], f'Подписчики пользователя {self.username} (@{self.username}) | MYANIMESITE'
        )
        self.assertEqual(
            list(context['object_list']),
            [follow_obj.user for follow_obj in Follow.objects.all().order_by('created_at')[24:48]],
        )

    def test_if_profile_does_not_exist(self):
        self.path = reverse('users:followers', kwargs={'username': 'test999'})
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class FollowingListViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.username = 'test_user'
        cls.password = '123456'
        cls.path = reverse('users:followings', kwargs={'username': cls.username})
        cls.user = User.objects.create_user(username=cls.username, email='test@gmail.com', password=cls.password)
        hashed_password = make_password(cls.password)
        users = [
            User(
                username=f'test_user{i}',
                email=f'test{i}@gmail.com',
                password=hashed_password,
            )
            for i in range(100, 150)
        ]
        User.objects.bulk_create(users)
        followers = [Follow(user=cls.user, following=user) for user in users]

        Follow.objects.bulk_create(followers)

    def test_happy_path(self):
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            context['page_title'], f'Подписки пользователя {self.username} (@{self.username}) | MYANIMESITE'
        )
        self.assertEqual(
            list(context['object_list']),
            [follow_obj.following for follow_obj in Follow.objects.all().order_by('created_at')[:24]],
        )

    def test_pagination(self):
        response = self.client.get(self.path + '?page=2')
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            context['page_title'], f'Подписки пользователя {self.username} (@{self.username}) | MYANIMESITE'
        )
        self.assertEqual(
            list(context['object_list']),
            [follow_obj.following for follow_obj in Follow.objects.all().order_by('created_at')[24:48]],
        )

    def test_if_profile_does_not_exist(self):
        self.path = reverse('users:followers', kwargs={'username': 'test999'})
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class ProfileSettingsViewTestCase(TestCase):
    def setUp(self):
        self.username = 'test'
        self.password = '123456'
        self.user = User.objects.create_user(
            username=self.username, email='test@gmail.com', password=self.password, avatar=create_image('test')
        )
        self.path = reverse('users:profile_settings')

        self.factory = RequestFactory()
        self.view = ProfileSettingsView()

    def test_view_get(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = response.json()
        self.assertIn('html', data)

        html = data['html']

        self.assertIn('name="username"', html)
        self.assertIn(f'value="{self.username}"', html)

        self.assertIn('name="avatar"', html)

    def test_post_profile_form(self):
        test_data = {'username': 'new_test', 'name': 'new_name', 'bio': 'new_bio', 'form': 'profile_form'}
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, test_data)
        user = User.objects.first()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(user.name, test_data['name'])
        self.assertEqual(user.username, test_data['username'])
        self.assertEqual(user.bio, test_data['bio'])

    def test_post_profile_form_invalid(self):
        old_user = User.objects.first()
        test_data = {
            'username': '',
            'name': 'new_name',
            'bio': 'new_bio',
            'is_history_public': True,
            'form': 'profile_form',
        }
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, test_data)
        data = response.json()
        html = data['html']
        new_user = User.objects.first()

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(new_user.name, old_user.name)
        self.assertEqual(new_user.username, old_user.username)
        self.assertEqual(new_user.bio, old_user.bio)
        self.assertEqual(new_user.is_history_public, old_user.is_history_public)
        self.assertIn('id_username_error', html)

    def test_post_avatar_form(self):
        old_user = User.objects.first()
        test_data = {'avatar': create_image('new_test'), 'form': 'avatar_form'}
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, test_data)
        new_user = User.objects.first()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(old_user.avatar, new_user.avatar)

    def test_post_avatar_form_invalid(self):
        old_user = User.objects.first()
        test_data = {'avatar': create_image('new_test', resolution=(1, 1)), 'form': 'avatar_form'}
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, test_data)
        data = response.json()
        html = data['html']
        new_user = User.objects.first()

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(new_user.avatar, old_user.avatar)
        self.assertIn('id_avatar_error', html)


class AccountSettingsViewTestCase(TestCase):
    def setUp(self):
        self.username = 'test'
        self.password = '123456'
        self.user = User.objects.create_user(
            username=self.username, email='test@gmail.com', password=self.password, avatar=create_image('test')
        )
        self.path = reverse('users:account_settings')

        self.factory = RequestFactory()
        self.view = AccountSettingsView()

    def test_view_get(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = response.json()
        self.assertIn('html', data)

        html = data['html']

        self.assertIn('name="old_password"', html)
        self.assertIn('name="new_password1"', html)
        self.assertIn('name="new_password2"', html)
        self.assertIn('name="email"', html)

    def test_post_password_form(self):
        old_user = User.objects.first()
        test_data = {
            'old_password': self.password,
            'new_password1': 'new_password12345',
            'new_password2': 'new_password12345',
            'form': 'password_form',
        }
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, test_data)
        new_user = User.objects.first()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(old_user.password, new_user.password)

    def test_post_password_form_invalid(self):
        old_user = User.objects.first()
        test_data = {
            'old_password': 'test',
            'new_password1': 'new_password12345',
            'new_password2': 'new_password12345',
            'form': 'password_form',
        }
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, test_data)
        html = response.json()['html']
        new_user = User.objects.first()

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(old_user.password, new_user.password)
        self.assertIn('id_old_password_error', html)

    def test_post_email_form(self):
        test_data = {'email': 'new_test@gmail.com', 'form': 'email_form'}
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, test_data)
        user = User.objects.first()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(user.email, test_data['email'])

    def test_post_email_form_invalid(self):
        old_user = User.objects.first()
        test_data = {'email': 'new_testgmail.com', 'form': 'email_form'}
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, test_data)
        html = response.json()['html']
        new_user = User.objects.first()

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(new_user.email, old_user.email)
        self.assertIn('id_email_error', html)


class SettingsViewTestCase(TestCase):
    def setUp(self):
        self.username = 'test'
        self.password = '123456'
        self.user = User.objects.create_user(
            username=self.username, email='test@gmail.com', password=self.password, avatar=create_image('test')
        )
        self.path = reverse('users:settings')

    def test_view_get(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path)
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], f'{self.username} (@{self.username}) | Настройки | MYANIMESITE')

    def test_view_get_404(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)


class CommunityViewTestCase(TestCase):
    def setUp(self):
        users = [User(username=f'test{i}', password='12345') for i in range(10)]
        User.objects.bulk_create(users)

        self.path = reverse('users:community')

    def _common_tests(self, response):
        context = response.context
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['page_title'], 'Сообщество | MYANIMESITE')

    @patch('users.views.ES_Q')
    def test_shows_all_users(self, mock_es_q):
        response = self.client.get(self.path)
        context = response.context

        self._common_tests(response)
        self.assertEqual(list(context['object_list']), list(User.objects.all()))
        mock_es_q.assert_not_called()

    @patch('users.views.UserDocument.search')
    def test_with_search_field(self, mock_document):
        result = User.objects.all()[:2]

        mock_query = mock_document.return_value.query
        mock_to_queryset = mock_query.return_value.to_queryset
        mock_to_queryset.return_value = result

        response = self.client.get(self.path + '?search_field=test')
        context = response.context

        self._common_tests(response)
        self.assertEqual(list(context['object_list']), list(result))
        mock_to_queryset.assert_called_once()


class ToggleFollowTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = (User(username=f'test{i}', password='123456') for i in range(10))
        User.objects.bulk_create(users)

    def setUp(self):
        self.username = 'test999'
        self.password = '123456'
        self.user = User.objects.create_user(username=self.username, password=self.password, id=999, is_verified=True)

        followings = [Follow(user=self.user, following=following) for following in User.objects.exclude(id=999)[:5]]
        Follow.objects.bulk_create(followings)
        self.following_ids = [following.following_id for following in Follow.objects.all()]

        self.path = lambda target_id: reverse('users:toggle_follow', kwargs={'target_id': target_id})

    def test_if_user_is_not_verified(self):
        follow_before = Follow.objects.all()
        self.client.login(username=self.username, password=self.password)
        self.user.is_verified = False
        self.user.save()
        response = self.client.post(self.path(self.user.id))
        messages = [m.message for m in get_messages(response.wsgi_request)]

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(list(Follow.objects.all()), list(follow_before))
        self.assertIn('Чтобы подписаться на пользователя вы обязаны верифицировать ваш аккаунт через почту!', messages)

    def test_if_user_follows_themself(self):
        follow_before = list(Follow.objects.all())
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path(self.user.id))

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(list(Follow.objects.all()), follow_before)

    def test_if_user_follows(self):
        follow_before = list(Follow.objects.all())
        self.client.login(username=self.username, password=self.password)
        target_id = User.objects.exclude(id__in=self.following_ids).exclude(id=self.user.id).first().id
        response = self.client.post(self.path(target_id))
        follow_after = Follow.objects.all()

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertNotEqual(list(follow_after), follow_before)
        self.assertTrue(follow_after.filter(following_id=target_id, user=self.user).exists())

    def test_if_user_unfollows(self):
        follow_before = list(Follow.objects.all())
        self.client.login(username=self.username, password=self.password)
        target_id = User.objects.filter(id__in=self.following_ids).exclude(id=self.user.id).first().id
        response = self.client.post(self.path(target_id))
        follow_after = Follow.objects.all()

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertNotEqual(list(follow_after), follow_before)
        self.assertFalse(follow_after.filter(following_id=target_id, user=self.user).exists())


class DeleteAvatarTestCase(TestCase):
    def setUp(self):
        self.username = 'test999'
        self.password = '123456'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.path = reverse('users:delete_avatar')

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_when_user_has_avatar(self):
        self.user.avatar = create_image('test')
        self.user.save()
        avatar_path = self.user.avatar.path

        self.client.login(username=self.username, password=self.password)
        self.assertTrue(User.objects.first().avatar)
        self.assertTrue(os.path.exists(avatar_path))

        response = self.client.post(self.path)
        self.assertFalse(User.objects.first().avatar)
        self.assertFalse(os.path.exists(avatar_path))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_when_user_does_not_has_avatar(self):
        self.assertFalse(self.user.avatar)
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path)
        self.assertFalse(User.objects.first().avatar)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
