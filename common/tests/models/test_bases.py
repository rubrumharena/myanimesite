import os
import tempfile
from unittest.mock import patch

from django.db import connection, models
from django.test import TestCase, override_settings

from common.models.bases import BaseListModel
from common.utils.testing_components import create_image


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class BaseListModelTestCase(TestCase):
    class TestModel(BaseListModel):
        image = models.ImageField(upload_to='Temp', null=True, blank=True)

        class Meta:
            app_label = 'lists'
            managed = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as schema:
            schema.create_model(cls.TestModel)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema:
            schema.delete_model(cls.TestModel)
        super().tearDownClass()

    @patch('common.models.bases.resize_image')
    def test_happy_path(self, mock_resize_image):
        image = create_image('test')
        model = self.TestModel.objects.create(name='test')
        model.image = image
        model.save()
        mock_resize_image.assert_called()
        self.assertTrue(os.path.exists(model.image.path))
