from django.test import RequestFactory, TestCase

from common.utils.testing_components import create_image
from lists.forms import FolderForm
from lists.models import Folder
from titles.models import Title
from users.models import User


class FolderFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.username = 'mrfreeze'
        cls.password = '12345'
        user = User.objects.create_user(username=cls.username, password=cls.password)
        folders = [Folder(name=f'Folder {i}', user=user) for i in range(5)]
        Folder.objects.bulk_create(folders)

    def setUp(self):
        self.base_form_data = {'name': 'Test Folder', 'description': 'Test', 'image': None, 'is_hidden': False}
        self.request = RequestFactory().get('/')
        self.request.user = User.objects.get(username=self.username)

    def test_form_initializes_data_initials(self):
        form = FolderForm(data=self.base_form_data, request=self.request)
        for field, value in self.base_form_data.items():
            with self.subTest(field=field, value=value):
                self.assertEqual(form[field].value(), value)

    def test_form_initializes_request_when_data_requires_filling(self):
        form = FolderForm(data=self.base_form_data, request=self.request)
        self.assertEqual(self.request, form.request)

        with self.assertRaises(TypeError):
            FolderForm(data=self.base_form_data)

    def test_form_does_not_require_request_for_view(self):
        form = FolderForm()
        self.assertIsNone(form.request)

    def test_form_gets_request(self):
        form = FolderForm(data=self.base_form_data, request=self.request)
        self.assertEqual(form.request, self.request)

    def test_when_changing_form_name(self):
        folder = Folder.objects.first()

        form = FolderForm(data=self.base_form_data, instance=folder, request=self.request)

        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Folder.objects.first().name, self.base_form_data['name'])

    def test_when_changing_form_name_with_existing_value(self):
        folder1 = Folder.objects.first()
        folder2 = Folder.objects.last()
        folder1.name = self.base_form_data['name']
        folder1.save()

        form = FolderForm(data=self.base_form_data, instance=folder2, request=self.request)
        self.assertFalse(form.is_valid())

    def test_when_form_placed_with_title_id(self):
        title = Title.objects.create(name='Title 1', id=1, type=Title.MOVIE)
        self.base_form_data['title_id'] = title.id

        form = FolderForm(data=self.base_form_data, request=self.request)
        self.assertTrue(form.is_valid())

    def test_when_form_title_id_is_incorrect(self):
        test_cases = [999, 'abc', 9.8]
        for case in test_cases:
            with self.subTest(case=case):
                self.base_form_data['title_id'] = case
                form = FolderForm(data=self.base_form_data, request=self.request)
                self.assertFalse(form.is_valid())

    def test_when_image_is_invalid(self):
        test_cases = [create_image('test1', (1, 1)), create_image('test2', mb=1000)]
        for case in test_cases:
            with self.subTest(case=case):
                form = FolderForm(data=self.base_form_data, files={'image': case}, request=self.request)
                self.assertFalse(form.is_valid())
