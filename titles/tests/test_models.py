import os
import tempfile
from http import HTTPStatus
from io import BytesIO
from unittest.mock import MagicMock, patch

import requests
from django.conf import settings
from django.contrib.admin import AdminSite
from django.test import RequestFactory, TestCase, override_settings
from PIL import Image

from common.utils.testing_components import create_image
from titles.admin import BackdropAdmin, PosterAdmin, TitleAdmin
from titles.models import Backdrop, Poster, Title


class TitleModelTestCase(TestCase):
    def setUp(self):
        self.title = Title.objects.create(kinopoisk_id=999, name='Title')

    @patch('services.kinopoisk_import.create_from_title_ids')
    def test_when_id_was_given_and_there_is_no_record_in_the_db(self, mock_create_from_title_ids):
        title = Title(kinopoisk_id=1)
        title.save()

        self.assertTrue(Title.objects.filter(kinopoisk_id=1).exists())
        mock_create_from_title_ids.called_once_with([1])

    @patch('services.kinopoisk_import.create_from_title_ids')
    def test_when_id_was_given_and_there_is_record_in_the_db(self, mock_create_from_title_ids):
        self.title.name = 'New Title'
        self.title.save()

        self.assertTrue(Title.objects.filter(kinopoisk_id=self.title.kinopoisk_id).exists())
        mock_create_from_title_ids.assert_not_called()

    @patch('services.kinopoisk_import.create_from_title_ids')
    def test_when_id_was_not_given(self, mock_create_from_title_ids):
        title = Title(name='Title')
        title.save()

        self.assertTrue(Title.objects.filter(name=self.title.name).exists())
        mock_create_from_title_ids.assert_not_called()


@override_settings(MEDIA_ROOT=settings.TEMP_DIR)
class PosterModelTestCase(TestCase):
    def setUp(self):
        self.small_res = '40x40'
        self.medium_res = '264x352'
        self.upload_to = 'posters'
        self.title = Title.objects.create(name='Title 1', id=1, type=Title.SERIES)
        self.poster = Poster.objects.create(title=self.title)
        self.poster_url = 'https://example.com/poster.jpg'
        self.fake_response = MagicMock()
        self.fake_response.status_code = HTTPStatus.OK
        self.session = MagicMock()

        self._fill_image_content()

    def _common_tests(self, resolution, filenames):
        poster = Poster.objects.get(title=self.title)
        original = poster.original
        self.assertEqual((original.width, original.height), resolution)
        self.assertTrue(original.url.__contains__(filenames[0]))

        medium = poster.medium
        self.assertEqual((medium.width, medium.height), (Poster.MEDIUM_WIDTH, Poster.MEDIUM_HEIGHT))
        self.assertTrue(medium.url.__contains__(filenames[1]))

        small = poster.small
        self.assertEqual((small.width, small.height), (Poster.SMALL_WIDTH, Poster.SMALL_HEIGHT))
        self.assertTrue(small.url.__contains__(filenames[2]))

    def _fill_image_content(self, mode='rgb', resolution=(400, 500), format='jpeg'):
        img = Image.new(mode=mode.upper(), size=resolution, color='red')
        buffer = BytesIO()
        img.save(buffer, format=format.upper())
        buffer.seek(0)
        self.fake_response.content = buffer.getvalue()

    def test_happy_path(self):
        self.session.get.return_value = self.fake_response
        filenames = [
            'Title_1',
            f'Title_1_{self.medium_res}',
            f'Title_1_{self.small_res}',
        ]

        return_value = self.poster.build(self.poster_url, self.session)
        self.poster.save()
        self._common_tests((400, 500), filenames)
        self.assertTrue(return_value)

    def test_when_url_is_invalid(self):
        self.fake_response.status_code = HTTPStatus.NOT_FOUND
        self.session.get.return_value = self.fake_response

        return_value = self.poster.build(self.poster_url, self.session)
        self.poster.save()
        poster = Poster.objects.get(title=self.title)

        self.assertFalse(poster.original)
        self.assertFalse(poster.medium)
        self.assertFalse(poster.small)
        self.assertFalse(return_value)

    def test_when_image_has_alpha_chanel(self):
        self._fill_image_content(mode='rgba', format='png')
        self.session.get.return_value = self.fake_response

        filenames = [
            'Title_1',
            f'Title_1_{self.medium_res}',
            f'Title_1_{self.small_res}',
        ]

        return_value = self.poster.build(self.poster_url, self.session)
        self.poster.save()
        self._common_tests((400, 500), filenames)
        self.assertTrue(return_value)

    def test_when_image_is_small(self):
        self._fill_image_content(resolution=(100, 100))
        self.session.get.return_value = self.fake_response

        return_value = self.poster.build(self.poster_url, self.session)
        self.poster.save()
        poster = Poster.objects.get(title=self.title)

        self.assertFalse(poster.original)
        self.assertFalse(poster.medium)
        self.assertFalse(poster.small)
        self.assertFalse(return_value)

    def test_when_image_has_incorrect_extension(self):
        self._fill_image_content(format='gif')
        self.session.get.return_value = self.fake_response

        return_value = self.poster.build(self.poster_url, self.session)
        self.poster.save()
        poster = Poster.objects.get(title=self.title)

        self.assertFalse(poster.original)
        self.assertFalse(poster.medium)
        self.assertFalse(poster.small)
        self.assertFalse(return_value)

    def test_when_500_error(self):
        self.fake_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        self.session.get.return_value = self.fake_response

        with self.assertRaises(requests.RequestException):
            self.poster.build(self.poster_url, self.session)

        self.poster.save()
        poster = Poster.objects.get(title=self.title)

        self.assertFalse(poster.original)
        self.assertFalse(poster.medium)
        self.assertFalse(poster.small)

    def test_when_429_error(self):
        self.fake_response.status_code = HTTPStatus.TOO_MANY_REQUESTS
        self.session.get.return_value = self.fake_response

        with self.assertRaises(requests.RequestException):
            self.poster.build(self.poster_url, self.session)

        self.poster.save()
        poster = Poster.objects.get(title=self.title)

        self.assertFalse(poster.original)
        self.assertFalse(poster.medium)
        self.assertFalse(poster.small)


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
