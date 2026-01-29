import tempfile
import os

from django.contrib.admin import AdminSite

from common.utils.testing_components import create_image
from lists.admin import FolderAdmin, CollectionAdmin
from users.models import User

from django.test import TestCase, RequestFactory, override_settings

from lists.models import Folder, Collection



@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class FolderTestCase(TestCase):

    def setUp(self):
        user = User.objects.create_user(username='user', password='123456')
        self.folders = [Folder(name=f'test{i}', image=create_image(f'test{i}'), user=user) for i in range(3)]
        Folder.objects.bulk_create(self.folders)

    def _image_tests(self, file_paths, instance, admin=None):
        for path in file_paths:
            self.assertTrue(os.path.exists(path))

        if admin:
            request = RequestFactory().post('/')
            admin.delete_queryset(request, instance)
        else:
            instance.delete()

        for path in file_paths:
            self.assertFalse(os.path.exists(path))

    def test_single_delete_removes_files(self):
        folder = self.folders[0]
        self._image_tests([folder.image.path], folder)


    def test_bulk_delete_removes_files(self):
        file_paths = [folder.image.path for folder in self.folders]
        self._image_tests(file_paths, Folder.objects.all())

    def test_admin_bulk_delete_removes_files(self):
        file_paths = [folder.image.path for folder in self.folders]
        self._image_tests(file_paths, Folder.objects.all(), FolderAdmin(Folder, AdminSite()))


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class CollectionTestCase(TestCase):

    def setUp(self):
        self.collections = [Collection(name=f'test{i}', image=create_image(f'test{i}'), slug=f'test{i}') for i in range(3)]
        Collection.objects.bulk_create(self.collections)

    def _image_tests(self, file_paths, instance, admin=None):
        for path in file_paths:
            self.assertTrue(os.path.exists(path))

        if admin:
            request = RequestFactory().post('/')
            admin.delete_queryset(request, instance)
        else:
            instance.delete()

        for path in file_paths:
            self.assertFalse(os.path.exists(path))

    def test_single_delete_removes_files(self):
        collection = self.collections[0]
        self._image_tests([collection.image.path], collection)

    def test_bulk_delete_removes_files(self):
        file_paths = [collection.image.path for collection in self.collections]
        self._image_tests(file_paths, Collection.objects.all())

    def test_admin_bulk_delete_removes_files(self):
        file_paths = [collection.image.path for collection in self.collections]
        self._image_tests(file_paths, Collection.objects.all(), CollectionAdmin(Collection, AdminSite()))
