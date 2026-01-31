import os
from types import SimpleNamespace
from unittest.mock import Mock

from django.core.files.storage import default_storage
from django.test import TestCase
from PIL import Image

from common.utils.files import delete_orphaned_files, resize_image
from common.utils.testing_components import create_image


class DeleteOrphansTestCase(TestCase):
    def test_deletes_files_as_args(self):
        files = [SimpleNamespace(path=create_image(f'test_{i}', (100, 100), save=True)) for i in range(3)]

        for file in files:
            with self.subTest(file=file):
                self.assertTrue(os.path.exists(file.path))

        delete_orphaned_files(*files)

        for file in files:
            with self.subTest(file=file):
                self.assertFalse(os.path.exists(file.path))

    def test_deletes_files_as_array(self):
        files = [SimpleNamespace(path=create_image(f'test_{i}', (100, 100), save=True)) for i in range(3)]

        for file in files:
            with self.subTest(file=file):
                self.assertTrue(os.path.exists(file.path))

        delete_orphaned_files(files)

        for file in files:
            with self.subTest(file=file):
                self.assertFalse(os.path.exists(file.path))

    def test_when_files_does_not_have_attribute_path(self):
        files = [create_image(f'test_{i}', (100, 100), save=True) for i in range(3)]

        for file in files:
            with self.subTest(file=file):
                self.assertTrue(os.path.exists(file))

        delete_orphaned_files(files)

        for file in files:
            with self.subTest(file=file):
                self.assertTrue(os.path.exists(file))


class ResizeImageTestCase(TestCase):
    def _common_tests(self, path, resolution, resized):
        image = Image.open(path)
        self.assertEqual(image.size, resolution)
        self.assertTrue(resized)
        image.close()
        default_storage.delete(path)

    def test_happy_path(self):
        resolution = (500, 500)
        path = create_image('test', resolution, save=True)
        image = Mock()
        image.path = path

        resized = resize_image(new=image, resolution=(100, 100))

        self._common_tests(path, (100, 100), resized)

    def test_if_image_has_small_resolution(self):
        resolution = (50, 50)
        path = create_image('test', resolution, save=True)
        image = Mock()
        image.path = path

        resized = resize_image(new=image, resolution=(100, 100))

        self._common_tests(path, resolution, resized)

    def test_if_old_was_given(self):
        resolution = (100, 100)
        path1 = create_image('test1', (200, 200), save=True)
        path2 = create_image('test2', (200, 200), save=True)
        image1 = Mock()
        image1.delete.side_effect = lambda save=False: default_storage.delete(path1)
        image2 = Mock()
        image2.path = path2

        resized = resize_image(new=image2, old=image1, resolution=resolution)

        self.assertFalse(os.path.exists(path1))
        self._common_tests(path2, resolution, resized)

    def test_if_old_was_given_and_new_is_none(self):
        resolution = (100, 100)
        path = create_image('test1', (200, 200), save=True)
        image = Mock()
        image.delete.side_effect = lambda save=False: default_storage.delete(path)

        resized = resize_image(old=image, resolution=resolution)

        self.assertFalse(resized)
        self.assertFalse(os.path.exists(path))

    def test_if_old_and_new_are_none(self):
        resolution = (100, 100)
        resized = resize_image(resolution=resolution)
        self.assertFalse(resized)
