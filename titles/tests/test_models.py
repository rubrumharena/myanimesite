import os
import tempfile
from http import HTTPStatus
from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
from django.contrib.admin import AdminSite
from django.test import RequestFactory, TestCase, override_settings
from PIL import Image

from common.utils.testing_components import TestTitleSetUpMixin, create_image
from lists.models import Collection
from titles.admin import BackdropAdmin, PosterAdmin, TitleAdmin
from titles.models import (Backdrop, Group, Person, Poster, SeasonsInfo,
                           Studio, Title)


class TitlePreSaveTestCase(TestTitleSetUpMixin, TestCase):
    def setUp(self):
        super().setUp()

    @override_settings(DEBUG_RETURN_TEST_VARS=True)
    def test_pre_save_when_new_data_comes(self):
        title = Title()

        saved_data = title._pre_save(new_info=self.fake_info)

        for attribute, value in self.data.items():
            with self.subTest(attribute=attribute, value=value):
                if attribute not in ('is_series', 'movie_length'):
                    self.assertEqual(getattr(saved_data, attribute), value)

        self.assertEqual(saved_data.duration, self.fake_info.movie_length)

    @override_settings(DEBUG_RETURN_TEST_VARS=True)
    def test_pre_save_when_data_comes_for_update(self):
        new_name = 'Евангелион 3.0'
        title = Title.objects.bulk_create([Title(name=new_name, id=1, kinopoisk_id=1, type=Title.SERIES)])[0]

        saved_data = title._pre_save(new_info=self.fake_info)

        for attribute, value in self.data.items():
            with self.subTest(attribute=attribute, value=value):
                if attribute not in ('is_series', 'movie_length', 'name', 'type'):
                    self.assertEqual(getattr(saved_data, attribute), value)

        self.assertEqual(new_name, saved_data.name)
        self.assertEqual(Title.SERIES, saved_data.type)
        self.assertEqual(self.fake_info.movie_length, saved_data.duration)

    @override_settings(DEBUG_RETURN_TEST_VARS=True)
    def test_pre_save_when_some_incoming_data_is_none(self):
        title = Title()
        self.fake_info.premiere = None
        self.fake_info.status = None
        self.fake_info.is_series = None
        self.fake_info.type = None

        saved_data = title._pre_save(new_info=self.fake_info)

        excluded_fields = ('is_series', 'premiere', 'status', 'type', 'movie_length')
        for attribute, value in self.data.items():
            with self.subTest(attribute=attribute, value=value):
                if attribute not in excluded_fields:
                    self.assertEqual(value, getattr(saved_data, attribute))

        for attribute in excluded_fields:
            with self.subTest(attribute=attribute):
                if attribute not in excluded_fields:
                    self.assertEqual(None, getattr(saved_data, attribute))


class TitlePostSaveTestCase(TestTitleSetUpMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.fake_info.title_id = 1
        self.fake_info.sequels_and_prequels = [2, 3, 4]
        self.fake_info.seasons_info = []

    @patch('titles.models.Title._attach_assets')
    @patch('titles.models.Title._link_related_entities')
    @patch('titles.models.Statistic.objects.update_or_create')
    def test_post_save_links_sequels_and_prequels(self, mock_attach_assets, mock_related_entities, mock_update):
        title = Title.objects.bulk_create((Title(name=f'Title {i}', id=i, kinopoisk_id=i) for i in range(1, 5)))[0]
        self.fake_info.seasons_info = [{'number': 1, 'episodesCount': 10}, {'number': 2, 'episodesCount': 10}]
        self.fake_info.is_series = True
        title._post_save(self.fake_info)

        for parent, children in [(1, self.fake_info.sequels_and_prequels)]:
            for child in children:
                self.assertTrue(Group.objects.filter(parent_id=parent, child_id=child).exists())

        self.assertEqual(SeasonsInfo.objects.count(), 20)

    @patch('titles.models.Title._attach_assets')
    @patch('titles.models.Title._link_related_entities')
    @patch('titles.models.Statistic.objects.update_or_create')
    def test_post_save_when_sequels_and_prequels_are_none(self, mock_attach_assets, mock_related_entities, mock_update):
        self.fake_info.sequels_and_prequels = []
        title = Title.objects.bulk_create([Title(name='Title 1', id=1, kinopoisk_id=1, type=Title.SERIES)])[0]

        title._post_save(self.fake_info)

        self.assertEqual(Group.objects.count(), 0)
        self.assertEqual(SeasonsInfo.objects.count(), 1)


class TitleOtherMethodsTestCase(TestTitleSetUpMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.fake_info.poster = 'https://www.example.com/1'

        self.title = Title.objects.bulk_create([Title(name='Title 1', id=1, kinopoisk_id=1, type=Title.SERIES)])[0]

    @patch('titles.models.Title.upload_poster')
    def test_attach_assets_when_only_poster_expect_no_upload_and_no_backdrops(self, mock_upload_poster):
        self.fake_info.poster = None

        self.title._attach_assets(self.fake_info)

        self.assertEqual(mock_upload_poster.call_count, 0)
        self.assertEqual(Backdrop.objects.count(), 0)

    @patch('titles.models.Title.upload_poster')
    def test_attach_assets_when_poster_and_backdrops_expect_upload_and_create_backdrops(self, mock_upload_poster):
        self.fake_info.backdrops = ['https://www.example.com/1', 'https://www.example.com/2']

        self.title._attach_assets(self.fake_info)

        self.assertEqual(mock_upload_poster.call_count, 1)
        self.assertEqual(Backdrop.objects.count(), 2)

    def test_link_related_entities_when_all_data_needs_to_be_stored(self):
        persons_count, genres_count, studios_count = 10, 5, 3
        self.fake_info.persons = [
            {
                'id': i,
                'name': f'Name {i}',
                'description': '',
                'enProfession': 'actor',
                'photo': f'https://www.example.com/{i}',
            }
            for i in range(1, persons_count + 1)
        ]
        self.fake_info.production_companies = [f'Studio {i}' for i in range(1, studios_count + 1)]
        self.fake_info.categories = [f'Genre {i}' for i in range(1, 4)]
        self.fake_info.keywords = [f'Keyword {i}' for i in range(1, 3)]

        self.title._link_related_entities(self.fake_info)

        self.assertEqual(persons_count, Person.objects.count())
        self.assertEqual(genres_count, Collection.objects.count())
        self.assertEqual(studios_count, Studio.objects.count())

    def test_link_related_entities_when_all_data_is_empty(self):
        self.fake_info.persons = []
        self.fake_info.production_companies = []
        self.fake_info.categories = []
        self.fake_info.keywords = []

        self.title._link_related_entities(self.fake_info)

        self.assertEqual(0, Person.objects.count())
        self.assertEqual(0, Collection.objects.count())
        self.assertEqual(0, Studio.objects.count())

    def test_link_related_entities_when_genres_exist(self):
        genres_range = list(range(1, 4))
        self.fake_info.categories = [f'Genre {i}' for i in genres_range]
        self.fake_info.keywords = []
        self.fake_info.persons = []
        self.fake_info.production_companies = []
        Collection.objects.bulk_create(
            (Collection(name=f'Genre {i}', type=Collection.GENRE, slug=f'genre{i}') for i in genres_range)
        )

        self.title._link_related_entities(self.fake_info)

        self.assertEqual(3, Collection.objects.count())


class TitleUploadPosterTestCase(TestCase):
    def setUp(self):
        self.small_res = '40x40'
        self.medium_res = '264x352'
        self.upload_to = 'posters'
        self.title = Title.objects.bulk_create([Title(name='Title 1', id=1, kinopoisk_id=1, type=Title.SERIES)])[0]
        self.poster = 'https://example.com/poster.jpg'
        self.fake_response = MagicMock()
        self.fake_response.status_code = HTTPStatus.OK

        self._create_image()

    def _common_tests(self, mock_save, mock_get, expected_data):
        mock_get.assert_called_once_with(self.poster)
        for call, expected in zip(mock_save.call_args_list, expected_data):
            args, kwargs = call
            self.assertEqual(args[0], expected)

    def _create_image(self, mode='rgb', resolution=(400, 500), format='jpeg'):
        img = Image.new(mode=mode.upper(), size=resolution, color='red')
        buffer = BytesIO()
        img.save(buffer, format=format.upper())
        buffer.seek(0)
        self.fake_response.content = buffer.getvalue()

    @patch('django.db.models.fields.files.FieldFile.save')
    @patch('titles.models.requests.get')
    def test_happy_path(self, mock_get, mock_save):
        mock_get.return_value = self.fake_response
        expected_filenames = [
            'Title_1.JPEG',
            f'Title_1_{self.medium_res}.JPEG',
            f'Title_1_{self.small_res}.JPEG',
        ]

        self.title.upload_poster(self.poster)
        self._common_tests(mock_save, mock_get, expected_filenames)

    @patch('django.db.models.fields.files.FieldFile.save')
    @patch('titles.models.requests.get')
    def test_when_url_is_incorrect(self, mock_get, mock_save):
        self.fake_response.status_code = HTTPStatus.NOT_FOUND
        mock_get.return_value = self.fake_response

        return_value = self.title.upload_poster(self.poster)

        self.assertEqual(return_value, None)

    @override_settings(DEBUG_RETURN_TEST_VARS=True)
    @patch('django.db.models.fields.files.FieldFile.save')
    @patch('titles.models.requests.get')
    def test_when_image_has_alpha_chanel(self, mock_get, mock_save):
        self._create_image(mode='rgba', format='png')

        mock_get.return_value = self.fake_response
        expected_filenames = [
            'Title_1.JPEG',
            'Title_1_{self.medium_res}.JPEG',
            'Title_1_{self.small_res}.JPEG',
        ]

        is_error = self.title.upload_poster(self.poster)

        self.assertTrue(is_error)
        self._common_tests(mock_save, mock_get, expected_filenames)

    @patch('django.db.models.fields.files.FieldFile.save')
    @patch('titles.models.requests.get')
    def test_when_image_is_small(self, mock_get, mock_save):
        self._create_image(resolution=(100, 100))
        mock_get.return_value = self.fake_response

        return_value = self.title.upload_poster(self.poster)

        self.assertEqual(return_value, None)

    @patch('django.db.models.fields.files.FieldFile.save')
    @patch('titles.models.requests.get')
    def test_when_image_is_big(self, mock_get, mock_save):
        arr = np.random.randint(0, 256, (5_000, 5_000, 3), dtype=np.uint8)
        img = Image.fromarray(arr, 'RGB')
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=95)

        self.fake_response.content = buffer.getvalue()
        mock_get.return_value = self.fake_response

        return_value = self.title.upload_poster(self.poster)

        self.assertEqual(return_value, None)

    @patch('django.db.models.fields.files.FieldFile.save')
    @patch('titles.models.requests.get')
    def test_when_image_has_incorrect_extension(self, mock_get, mock_save):
        self._create_image(format='gif')
        mock_get.return_value = self.fake_response

        return_value = self.title.upload_poster(self.poster)

        self.assertEqual(return_value, None)


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class TitleDeleteTestCase(TestCase):
    def setUp(self):
        self.titles = []

        for i in range(3):
            title = Title.objects.create(name=f'Name {i}')

            Poster.objects.create(
                title=title,
                original=create_image('original'),
                medium=create_image('medium'),
                small=create_image('small'),
            )

            Backdrop.objects.create(title=title, backdrop_local=create_image('backdrop_local'))
            self.titles.append(title)

    def _common_tests(self, file_paths, instance, admin=None):
        for path in file_paths:
            self.assertTrue(os.path.exists(path))

        if admin:
            request = RequestFactory().post('/')
            admin.delete_queryset(request, instance)
        else:
            instance.delete()

        for path in file_paths:
            self.assertFalse(os.path.exists(path))

    def test_title__single_delete_removes_files(self):
        title = self.titles[0]

        self._common_tests([file.path for file in title.media_files], title)

    def test_title__bulk_delete_removes_files(self):
        files = []
        for title in self.titles:
            files.extend(title.media_files)
        file_paths = [file.path for file in files]

        self._common_tests(file_paths, Title.objects.all())

    def test_title__admin_bulk_delete_removes_files(self):
        files = []
        for title in self.titles:
            files.extend(title.media_files)
        file_paths = [file.path for file in files]

        self._common_tests(file_paths, Title.objects.all(), TitleAdmin(Title, AdminSite()))

    def test_poster__single_delete_removes_files(self):
        title = self.titles[0]

        self._common_tests([file.path for file in title.poster.media_files], title.poster)

    def test_poster__bulk_delete_removes_files(self):
        posters = Poster.objects.all()
        files = []
        for poster in posters:
            files.extend(poster.media_files)
        file_paths = [file.path for file in files]

        self._common_tests(file_paths, posters)

    def test_poster__admin_bulk_delete_removes_files(self):
        posters = Poster.objects.all()
        files = []
        for poster in posters:
            files.extend(poster.media_files)
        file_paths = [file.path for file in files]

        self._common_tests(file_paths, posters, PosterAdmin(Poster, AdminSite()))

    def test_backdrop__single_delete_removes_files(self):
        title = self.titles[0]
        backdrop = title.backdrops.first()
        self._common_tests([backdrop.backdrop_local.path], backdrop)

    def test_backdrop__bulk_delete_removes_files(self):
        backdrops = Backdrop.objects.all()

        self._common_tests([backdrop.backdrop_local.path for backdrop in backdrops], backdrops)

    def test_backdrop__test_admin_bulk_delete_removes_files(self):
        backdrops = Backdrop.objects.all()

        self._common_tests(
            [backdrop.backdrop_local.path for backdrop in backdrops], backdrops, BackdropAdmin(Backdrop, AdminSite())
        )
