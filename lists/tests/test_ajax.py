import json
from http import HTTPStatus
from unittest.mock import patch, MagicMock

from django.contrib.postgres.aggregates import ArrayAgg
from django.shortcuts import reverse
from django.test import TestCase

from common.utils.enums import FolderMethod
from common.utils.ui import generate_years_and_decades
from titles.models import Title, Statistic, RatingHistory, SeasonsInfo
from users.models import User
from lists.models import Collection, Folder


class GetCollectionsTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        mov_collections = (
        Collection(name=f'Super Movie Collection {i}', type=Collection.MOVIE_COLLECTION, slug=f'mov_{i}') for i in
        range(1, 6))
        Collection.objects.bulk_create(mov_collections)
        ser_collections = (
        Collection(name=f'Super Series Collection {i}', type=Collection.SERIES_COLLECTION, slug=f'ser_{i}') for i in
        range(1, 6))
        Collection.objects.bulk_create(ser_collections)
        genres = (Collection(name=f'Genre {i}', type=Collection.GENRE, slug=f'gen_{i}') for i in range(1, 11))
        Collection.objects.bulk_create(genres)

    def setUp(self):
        self.path = reverse('lists:get_collections_ajax') + '?type='

    def _common_tests(self, response, expected_data):
        actual_data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        for case in expected_data:
            with self.subTest(case=case):
                self.assertIn(case, actual_data['items'])

    def test_when_title_count_is_zero(self):
        response = self.client.get(self.path + Collection.GENRE)
        expected_data = [
            {
                'name': f'Genre {i}',
                'image': None,
                'title_count': 0,
                'type': Collection.GENRE,
                'url': reverse('lists:collection') + f'genre--gen_{i}/',
            } for i in range(1, 11)
        ]
        self._common_tests(response, expected_data)

    def test_happy_path(self):
        titles = [Title(name=f'Title {i}', id=i) for i in range(1, 6)]
        Title.objects.bulk_create(titles)

        collection1 = Collection.objects.get(id=1, type=Collection.MOVIE_COLLECTION)
        collection2 = Collection.objects.get(id=2, type=Collection.MOVIE_COLLECTION)

        for title in titles[:3]:
            title.collections.add(collection1)
        for title in titles[3:]:
            title.collections.add(collection2)

        response = self.client.get(self.path + Collection.MOVIE_COLLECTION)

        expected_data = [
            {
                'name': f'Super Movie Collection {i + 1}',
                'image': None,
                'title_count': j,
                'type': Collection.MOVIE_COLLECTION,
                'url': reverse('lists:collection') + f'mov_{i + 1}/',
            } for i, j in enumerate([3, 2, 0, 0, 0])
        ]
        self._common_tests(response, expected_data)

    def test_when_collection_is_years(self):
        response = self.client.get(self.path + Collection.YEAR)

        expected_data = [
            {
                'name': year + ' год' if '-' not in year else year[:4] + '-е',
                'image': None,
                'title_count': None,
                'type': Collection.YEAR,
                'url': Collection().generate_url(Collection.YEAR, year),
            } for year in generate_years_and_decades(10, True)
        ]
        self._common_tests(response, expected_data)

    def test_when_collection_type_is_incorrect(self):
        response = self.client.get(self.path + 'test')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(json.loads(response.content.decode()), {'items': []})


class FolderManagementTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.password = '12345'
        cls.username = 'user_1'

        [User.objects.create_user(username=f'user_{i}', password=cls.password, email=f'email_test{i}') for i in
         range(1, 3)]

        titles = (Title(name=f'Title {i}', id=i, type=Title.MOVIE) for i in range(1, 11))
        Title.objects.bulk_create(titles)

    def setUp(self):
        self.get_folders_path = reverse('lists:get_user_folders_ajax')
        self.save_folder_path = reverse('lists:save_folder_ajax')
        self.update_folder_path = reverse('lists:update_folder_titles_ajax')

        titles = Title.objects.all()
        users = User.objects.all()

        folder_objects = []
        for user in users:
            folder_objects += [Folder(user=user, name=f'Folder {i} {user.username}') for i in range(1, 6)]
        Folder.objects.bulk_create(folder_objects)

        link_model = Folder.titles.through
        folders = Folder.objects.all()
        links = []
        i = 0
        for folder in folders:
            links += [link_model(folder=folder, title=title) for title in titles[i: i + 2]]
            i += 2
        link_model.objects.bulk_create(links)

        self.base_test_data = {'folder_id': Folder.objects.first().id, 'title_id': titles.last().id,
                               'method': FolderMethod.ADD.value}

    def _common_update_form_tests(self, expected_titles, actual_titles, response=None):
        if response:
            self.assertEqual(response.status_code, HTTPStatus.OK)

        for actual_title, expected_title in zip(actual_titles.all().order_by('id'), expected_titles):
            with self.subTest(actual=actual_title.id, expected=expected_title):
                self.assertEqual(actual_title.id, expected_title)
        self.assertEqual(actual_titles.count(), len(expected_titles))

    def test_get_user_folders_happy_path(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(self.get_folders_path)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        folders = Folder.objects.filter(user__username=self.username).annotate(
            title_ids=ArrayAgg('titles__id', distinct=True)).only('id', 'name').order_by('-updated_at')
        expected_data = [{'id': folder.id,
                          'name': folder.name,
                          'folder_titles': folder.title_ids if all(folder.title_ids) else []} for folder in folders]
        self.assertEqual(json.loads(response.content.decode())['items'], list(expected_data))

    def test_get_user_folders_if_folder_does_not_have_any_titles(self):
        self.client.login(username=self.username, password=self.password)
        for folder in Folder.objects.filter(user__username=self.username):
            folder.titles.clear()

        response = self.client.get(self.get_folders_path)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        folders = Folder.objects.filter(user__username=self.username).only('id', 'name').order_by('-updated_at')
        expected_data = [{'id': folder.id,
                          'name': folder.name,
                          'folder_titles': []} for folder in folders]
        self.assertEqual(json.loads(response.content.decode())['items'], list(expected_data))

    def test_get_user_folders_when_user_is_unauthorized(self):
        response = self.client.get(self.get_folders_path)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_save_folder_happy_path(self):
        data = {'name': 'Test Folder', 'description': 'Test', 'is_hidden': False}
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.save_folder_path, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_save_folder_invalid(self):
        data = {'name': f'Folder 1 {self.username}', 'description': 'Test', 'is_hidden': False}
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.save_folder_path, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(json.loads(response.content.decode())['errors']['name'],
                         ['Такое название для папки уже существует'])

    def test_update_folder_titles_with_add_method(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.update_folder_path, self.base_test_data)

        self._common_update_form_tests([1, 2, 10], Folder.objects.get(id=self.base_test_data['folder_id']).titles,
                                       response)

    def test_update_folder_titles_with_delete_method(self):
        self.client.login(username=self.username, password=self.password)
        self.base_test_data['method'] = FolderMethod.DELETE.value
        self.base_test_data['title_id'] = 2

        response = self.client.post(self.update_folder_path, self.base_test_data)

        self._common_update_form_tests([1], Folder.objects.get(id=self.base_test_data['folder_id']).titles, response)

    def test_update_folder_titles_with_invalid_method(self):
        self.client.login(username=self.username, password=self.password)
        self.base_test_data['method'] = 'test'

        response = self.client.post(self.update_folder_path, self.base_test_data)

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self._common_update_form_tests([1, 2], Folder.objects.get(id=self.base_test_data['folder_id']).titles)

    def test_update_folder_titles_with_add_method_when_title_exists(self):
        self.client.login(username=self.username, password=self.password)
        self.base_test_data['title_id'] = 2
        response = self.client.post(self.update_folder_path, self.base_test_data)

        self._common_update_form_tests([1, 2], Folder.objects.get(id=self.base_test_data['folder_id']).titles, response)

    def test_update_folder_titles_with_fail_cases(self):
        self.client.login(username=self.username, password=self.password)
        test_cases = ['test', '', []]

        for test_case in test_cases:
            with self.subTest(case=test_case):
                self.base_test_data['title_id'] = test_case
                response = self.client.post(self.update_folder_path, self.base_test_data)
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        for test_case in test_cases:
            with self.subTest(case=test_case):
                self.base_test_data['folder_id'] = test_case
                response = self.client.post(self.update_folder_path, self.base_test_data)
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_update_folder_titles_with_404(self):
        self.client.login(username=self.username, password=self.password)
        self.base_test_data['title_id'] = 999

        response = self.client.post(self.update_folder_path, self.base_test_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.base_test_data['folder_id'] = 999

        response = self.client.post(self.update_folder_path, self.base_test_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
