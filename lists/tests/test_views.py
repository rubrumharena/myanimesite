import json
from http import HTTPStatus
from unittest.mock import patch

from django.db.models import Count
from django.shortcuts import reverse
from django.test import TestCase, override_settings

from common.utils.ui import generate_years_and_decades
from lists.models import Collection, Folder
from titles.models import Title
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

        self.path = reverse('lists:folder', kwargs={'folder_id': folder.id})

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
        self.assertFalse(response.context.get('is_editable'))

    @patch('lists.views.reverse')
    def test_get_context_data_if_user_visits_favorites(self, mock_reverse):
        self.client.login(username=self.username, password=self.password)
        user = User.objects.get(username=self.username)
        folder = Folder.objects.create(type=Folder.SYSTEM, user=user)

        path = reverse('lists:folder', kwargs={'folder_id': folder.id})
        mock_reverse.return_value = path
        page_title = (
            f'Папка "{folder.name}" пользователя {folder.user.username} (@{folder.user.username}) | MYANIMESITE'
        )

        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['page_title'], page_title)
        self.assertFalse(response.context.get('is_editable'))

    @patch('lists.views.reverse')
    def test_get_context_data__happy_path(self, mock_reverse):
        self.client.login(username=self.username, password=self.password)
        folder = Folder.objects.get(name='Folder 1')

        path = reverse('lists:folder', kwargs={'folder_id': folder.id})
        mock_reverse.return_value = path
        page_title = (
            f'Папка "{folder.name}" пользователя {folder.user.username} (@{folder.user.username}) | MYANIMESITE'
        )

        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['page_title'], page_title)
        self.assertTrue(response.context.get('is_editable'))


class FolderFormTestCase(TestCase):
    def setUp(self):
        self.password = '12345'
        self.username = 'test_user'
        self.user = User.objects.create_user(username=self.username, email='email1', password=self.password)
        self.folder = Folder.objects.create(name='Folder 1', user=self.user)
        self.path = reverse('lists:folder_form')

        self.test_data = {'name': 'Test Folder', 'description': 'Test', 'is_hidden': False}

    def test_update__form_valid(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path + f'?folder_id={self.folder.id}', self.test_data)
        data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(Folder.objects.filter(name=self.test_data['name']).exists())
        self.assertEqual(data['redirect'], reverse('lists:folder', kwargs={'folder_id': self.folder.id}))
        self.assertEqual(Folder.objects.count(), 2)

    def test_create__form_valid(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path, self.test_data)
        data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(Folder.objects.filter(name=self.test_data['name']).exists())
        self.assertIsNone(data.get('redirect'))
        self.assertEqual(Folder.objects.count(), 3)

    def test_form_invalid(self):
        Folder.objects.create(name=self.test_data['name'], user=self.user)
        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path, self.test_data)
        data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertTrue(Folder.objects.filter(name=self.test_data['name']).exists())
        self.assertTrue(data.get('html'))
        self.assertTemplateUsed(response, 'lists/modal_windows/_folder_popup.html')
        self.assertEqual(Folder.objects.count(), 3)

    def test_get_form_kwargs__when_invalid_folder_id(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path + '?folder_id=abc', self.test_data)
        data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(Folder.objects.filter(name=self.test_data['name']).exists())
        self.assertIsNone(data.get('redirect'))
        self.assertEqual(Folder.objects.count(), 3)

    def test_get__when_title_id_was_given(self):
        title = Title.objects.create(name='Title')
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(self.path + f'?title_id={title.id}')
        data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(data.get('redirect'))
        self.assertEqual(Folder.objects.count(), 2)
        self.assertTrue(data.get('html'))

    def test_get__happy_path(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(self.path)
        data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(data.get('redirect'))
        self.assertEqual(Folder.objects.count(), 2)
        self.assertIn('id="id_title"', data.get('html'))


class GetFolders(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = '12345'
        cls.username = 'user_1'

        cls.user1 = User.objects.create_user(username=cls.username, password=cls.password)
        cls.user2 = User.objects.create_user(username='another', password=cls.password)

        folders1 = [Folder(name=f'Folder {cls.user1.username} {i}', user=cls.user1) for i in range(5)]
        folders2 = [Folder(name=f'Folder {cls.user2.username} {i}', user=cls.user2) for i in range(5)]
        folders3 = [
            Folder(name=f'Folder {cls.user1.username} {i} pinned', user=cls.user1, is_pinned=True) for i in range(3)
        ]
        Folder.objects.bulk_create(folders1 + folders2 + folders3)

        titles = (Title(name=f'Title {i}', id=i, type=Title.MOVIE) for i in range(1, 11))
        Title.objects.bulk_create(titles)

        cls.folder = Folder.objects.filter(user=cls.user1).first()
        link_model = Folder.titles.through
        links = [link_model(title=title, folder=cls.folder) for title in Title.objects.all()]
        link_model.objects.bulk_create(links)

    def setUp(self):
        self.title = Title.objects.first()
        self.path = reverse('lists:get_folders', args=(self.title.id,))

    def _common_tests(self, user, response, mock):
        self.assertEqual(response.status_code, HTTPStatus.OK)
        args, kwargs = mock.call_args
        context = args[1]
        pinned_folders = Folder.objects.filter(user=user, is_pinned=True).order_by(
            '-type', '-is_pinned', '-updated_at', '-id'
        )
        not_pinned_folders = Folder.objects.filter(user=user, is_pinned=False).order_by(
            '-type', '-is_pinned', '-updated_at', '-id'
        )
        self.assertEqual(context['title'], self.title)
        self.assertEqual(list(context['folders']), list(pinned_folders) + list(not_pinned_folders))

    @patch('lists.views.render_to_string', return_value='')
    def test_get_user_folders_happy_path(self, mock_render_to_string):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path)
        args, kwargs = mock_render_to_string.call_args
        context = args[1]
        self._common_tests(self.user1, response, mock_render_to_string)
        self.assertTrue(context['folders'].get(id=self.folder.id).is_checked)

        for folder in context['folders'].exclude(id=self.folder.id):
            with self.subTest(folder=folder.id):
                self.assertFalse(folder.is_checked)

    @patch('lists.views.render_to_string', return_value='')
    def test_get_user_folders_if_folder_does_not_have_any_titles(self, mock_render_to_string):
        self.client.login(username=self.user2.username, password=self.password)
        response = self.client.get(self.path)
        args, kwargs = mock_render_to_string.call_args
        context = args[1]
        self._common_tests(self.user2, response, mock_render_to_string)

        for folder in context['folders']:
            with self.subTest(folder=folder.id):
                self.assertFalse(folder.is_checked)

    def test_get_user_folders_when_user_is_unauthorized(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)


class ToggleFolderTitleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = '12345'
        cls.username = 'user_1'
        cls.user = User.objects.create_user(username=cls.username, password=cls.password)
        titles = (Title(name=f'Title {i}', type=Title.MOVIE) for i in range(1, 11))
        Title.objects.bulk_create(titles)

    def setUp(self):
        titles = Title.objects.all()
        self.folder_titles = list(titles.order_by('id')[:7])

        self.folder = Folder.objects.create(user=self.user, name='Folder first')

        link_model = Folder.titles.through
        links = [link_model(folder=self.folder, title=title) for title in self.folder_titles]
        link_model.objects.bulk_create(links)

        self.path = lambda title_id, folder_id=self.folder.id: reverse(
            'lists:toggle_folder_title', kwargs={'folder_id': folder_id, 'title_id': title_id}
        )

    def _common_tests(self, expected_titles, response=None, status=HTTPStatus.OK):
        actual_titles = self.folder.titles.all().order_by('id')

        self.assertEqual(response.status_code, status)

        for actual_title, expected_title in zip(actual_titles, expected_titles):
            with self.subTest(actual=actual_title.id, expected=expected_title.id):
                self.assertEqual(actual_title, expected_title)
        self.assertEqual(actual_titles.count(), len(expected_titles))

    def test_toggle_folder_title__with_add_method(self):
        self.client.login(username=self.username, password=self.password)
        title = Title.objects.create(name='Title New', type=Title.MOVIE)

        response = self.client.post(self.path(title_id=title.id))
        self.folder_titles.append(title)
        self._common_tests(self.folder_titles, response, HTTPStatus.CREATED)

    def test_toggle_folder_title__with_delete_method(self):
        self.client.login(username=self.username, password=self.password)
        title = self.folder_titles.pop()
        response = self.client.post(self.path(title_id=title.id))

        self._common_tests(self.folder_titles, response)

    def test_toggle_folder_title__with_404(self):
        self.client.login(username=self.username, password=self.password)
        title = self.folder_titles[0]
        response = self.client.post(self.path(title_id=999))
        self._common_tests(self.folder_titles, response, HTTPStatus.NOT_FOUND)

        response = self.client.post(self.path(title_id=title.id, folder_id=999))
        self._common_tests(self.folder_titles, response, HTTPStatus.NOT_FOUND)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
)
class GetCollectionsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        mov_collections = (
            Collection(name=f'Super Movie Collection {i}', type=Collection.MOVIE_COLLECTION, slug=f'mov_{i}')
            for i in range(1, 6)
        )
        Collection.objects.bulk_create(mov_collections)
        ser_collections = (
            Collection(name=f'Super Series Collection {i}', type=Collection.SERIES_COLLECTION, slug=f'ser_{i}')
            for i in range(1, 6)
        )
        Collection.objects.bulk_create(ser_collections)
        genres = (Collection(name=f'Genre {i}', type=Collection.GENRE, slug=f'gen_{i}') for i in range(1, 11))
        Collection.objects.bulk_create(genres)

    def setUp(self):
        self.path = lambda c_type: reverse('lists:get_collections', args=[c_type])

    def _common_tests(self, response, expected_data):
        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(list(context['collections']), list(expected_data))

    def test_when_title_count_is_zero(self):
        response = self.client.get(self.path(Collection.GENRE))
        collections = (
            Collection.objects.annotate(title_count=Count('titles'))
            .filter(type=Collection.GENRE)
            .only('name', 'image', 'type')
            .order_by('name')
        )

        self._common_tests(response, collections)

    def test_happy_path(self):
        titles = [Title(name=f'Title {i}', id=i) for i in range(1, 6)]
        Title.objects.bulk_create(titles)

        collection1 = Collection.objects.filter(type=Collection.MOVIE_COLLECTION).first()
        collection2 = Collection.objects.filter(type=Collection.MOVIE_COLLECTION).last()

        for title in titles[:3]:
            collection1.titles.add(title)
        for title in titles[3:]:
            collection2.titles.add(title)

        response = self.client.get(self.path(Collection.MOVIE_COLLECTION))

        collections = (
            Collection.objects.annotate(title_count=Count('titles'))
            .filter(type=Collection.MOVIE_COLLECTION)
            .only('name', 'image', 'type')
            .order_by('name')
        )
        self._common_tests(response, collections)

    def test_when_collection_is_years(self):
        response = self.client.get(self.path(Collection.YEAR))

        collections = [
            {
                'name': year + ' год' if '-' not in year else year[:4] + '-е',
                'image': None,
                'title_count': None,
                'type': Collection.YEAR,
                'url': reverse('lists:collection') + f'year--{year}/',
            }
            for year in generate_years_and_decades(10, True)
        ]
        self._common_tests(response, collections)

    def test_when_collection_type_is_incorrect(self):
        response = self.client.get(self.path('test'))

        context = response.context

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(list(context['collections']), [])
