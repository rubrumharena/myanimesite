import itertools
import urllib
from datetime import date
from http import HTTPStatus
from unittest.mock import patch, MagicMock, PropertyMock
from urllib.parse import urlparse, parse_qs

from django.db.models import QuerySet
from django.http import Http404, QueryDict, HttpResponse
from django.test import TestCase, RequestFactory
from django.shortcuts import reverse
from django.views.generic import TemplateView, ListView
from django.views.generic.base import ContextMixin

from common.utils.enums import ListQueryParam, ListQueryValue, ListSortOption
from common.views.bases import BaseListView
from lists.forms import FolderForm
from lists.models import Collection, Folder
from titles.models import Title, Statistic
from users.models import User


class FolderDeleteViewTestCase(TestCase):

    def setUp(self):
        self.password = '12345'
        self.username = 'test_user'
        user = User.objects.create_user(username=self.username, email='email1', password=self.password)
        folder = Folder.objects.create(name='Folder 1', user=user)

        self.path = reverse('lists:delete_folder', kwargs={'folder_id': folder.id})

    def test_happy_path(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Folder.objects.count(), 1)

    def test_when_user_deletes_not_their_folder(self):
        user = User.objects.create_user(username='test_user2', email='email2', password=self.password)

        self.client.login(username=user.username, password=self.password)

        response = self.client.post(self.path)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(Folder.objects.count(), 3)

    def test_when_folder_id_is_invalid(self):
        self.client.login(username=self.username, password=self.password)

        path = reverse('lists:delete_folder', kwargs={'folder_id': 9999})
        response = self.client.post(path)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(Folder.objects.count(), 2)

    def test_when_unauthorized_user_visits_url(self):
        response = self.client.post(self.path)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Folder.objects.count(), 2)


class FolderListViewTestCase(TestCase):

    def setUp(self):
        self.password = '12345'
        self.username = 'test_user'
        user = User.objects.create_user(username=self.username, email='email1', password=self.password)
        folder = Folder.objects.create(name='Folder 1', user=user)
        titles = [Title(name=f'Title {i}', id=i, type=Title.MOVIE) for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        for title in titles:
            folder.titles.add(title)


        user = User.objects.create_user(username='test_user2', email='email2', password=self.password)
        Folder.objects.create(name='Folder 2', user=user, is_hidden=True)

        self.test_data = {'update-name': 'New Name', 'form': 'update_folder_form'}
        self.path = reverse('lists:folder', kwargs={'folder_id': folder.id})

    def test_post__when_update_folder_does_not_matches(self):
        self.test_data['form'] = 'test'
        response = self.client.post(self.path, self.test_data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertFalse(Folder.objects.filter(name=self.test_data['update-name']).exists())

    def test_post__user_is_not_owner_of_the_folder(self):
        response = self.client.post(self.path, self.test_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertFalse(Folder.objects.filter(name=self.test_data['update-name']).exists())

    @patch('lists.views.FolderListView.get_context_data', return_value={})
    @patch('lists.views.FolderListView.get_queryset', return_value=Title.objects.none())
    def test_post__form_is_invalid(self, mock_get_queryset, mock_get_context):
        self.client.login(username=self.username, password=self.password)

        self.test_data['update-name'] = ''
        response = self.client.post(self.path, self.test_data)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        mock_get_queryset.assert_called_once()
        mock_get_context.assert_called_once()
        self.assertTrue(Folder.objects.filter(name='Folder 1').exists())

    def test_post__happy_path(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path, self.test_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertTrue(Folder.objects.filter(name=self.test_data['update-name']).exists())

    def test_get_queryset__folder_is_hidden_for_user(self):
        folder = Folder.objects.get(name='Folder 2')
        path = reverse('lists:folder', kwargs={'folder_id': folder.id})
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(list(response.context['object_list']), list(Title.objects.none()))

    def test_get_queryset__happy_path(self):
        self.client.login(username=self.username, password=self.password)

        folder = Folder.objects.get(name='Folder 1')
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        print(list(response.context['object_list']), list(folder.titles.order_by('created_at')))
        self.assertEqual(list(response.context['object_list']), list(folder.titles.order_by('created_at')))

    @patch('lists.views.reverse')
    def test_get_context_data_if_user_visits_not_their_folder(self, mock_reverse):
        self.client.login(username=self.username, password=self.password)
        folder = Folder.objects.get(name='Folder 2')
        path = reverse('lists:folder', kwargs={'folder_id': folder.id})
        mock_reverse.return_value = path
        page_title = f'Приватная папка пользователя {folder.user.username} (@{folder.user.username}) | MYANIMESITE'

        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['page_title'], page_title)
        self.assertIsNone(response.context.get('update_folder_form'))

    @patch('lists.views.reverse')
    def test_get_context_data_if_user_visits_favorites(self, mock_reverse):
        self.client.login(username=self.username, password=self.password)
        user = User.objects.get(username=self.username)
        folder = Folder.objects.create(name=Folder.FAVORITES, user=user)

        path = reverse('lists:folder', kwargs={'folder_id': folder.id})
        mock_reverse.return_value = path
        page_title = f'Папка "{folder.name}" пользователя {folder.user.username} (@{folder.user.username}) | MYANIMESITE'

        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['page_title'], page_title)
        self.assertIsNone(response.context.get('update_folder_form'))

    @patch('lists.views.reverse')
    def test_get_context_data__happy_path(self, mock_reverse):
        self.client.login(username=self.username, password=self.password)
        folder = Folder.objects.get(name='Folder 1')

        path = reverse('lists:folder', kwargs={'folder_id': folder.id})
        mock_reverse.return_value = path
        page_title = f'Папка "{folder.name}" пользователя {folder.user.username} (@{folder.user.username}) | MYANIMESITE'

        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['page_title'], page_title)
        self.assertIsInstance(response.context.get('update_folder_form'), FolderForm)


