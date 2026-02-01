from io import BytesIO
from itertools import chain
from unittest.mock import MagicMock

import numpy as np
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from titles.models import SeasonsInfo, Title
from users.models import User
from video_player.models import VideoResource, ViewingHistory, VoiceOver


class TestJoinMixin:
    def _common_tests(self, data, miss_links=False):
        for obj in chain.from_iterable(data.values()):
            self.assertTrue(self.model.objects.filter(**{self.related_field.split('__')[1]: obj}).exists())

        self.assertEqual(self.model.objects.count(), len(set(chain.from_iterable(data.values()))))
        if not miss_links:
            self.assertEqual(self.related_model.objects.count(), len(list(chain.from_iterable(data.values()))))
        for title_id, related_objs in data.items():
            for obj in related_objs:
                kwargs = {'title_id': title_id, self.related_field: obj}
                self.assertTrue(self.related_model.objects.filter(**kwargs).exists())


class TestTitleSetUpMixin:
    def setUp(self):
        self.data = {
            'name': 'Евангелион',
            'year': 1999,
            'type': Title.MOVIE,
            'is_series': False,
            'movie_length': 120,
            'alternative_name': 'Evangeloin',
            'status': 'completed',
            'overview': 'Overview',
            'age_rating': 18,
            'tagline': 'Tagline',
            'premiere': '1999-01-01',
            'names': ['Name1', 'Name2', 'Name3'],
        }
        self.fake_info = MagicMock()

        for attribute, value in self.data.items():
            setattr(self.fake_info, attribute, value)

        self.fake_info.ratings = {'kp': 7.2, 'imdb': 7.1}
        self.fake_info.votes = {'kp': 892, 'imdb': 1743}


class TestVideoPlayerSetUpMixin:
    @classmethod
    def setUpTestData(cls):
        cls.voiceover1 = VoiceOver.objects.create(name='1')
        cls.voiceover2 = VoiceOver.objects.create(name='2')

        cls.series = Title.objects.create(name='Series', type=Title.SERIES)

        content1 = SeasonsInfo.objects.create(title=cls.series, episode=1, season=1)
        content2 = SeasonsInfo.objects.create(title=cls.series, episode=2, season=1)
        content3 = SeasonsInfo.objects.create(title=cls.series, episode=1, season=2)
        content4 = SeasonsInfo.objects.create(title=cls.series, episode=2, season=2)

        cls.ser_resource1 = VideoResource.objects.create(
            iframe='http://example/video_1', voiceover=cls.voiceover1, content_unit=content1
        )
        cls.ser_resource2 = VideoResource.objects.create(
            iframe='http://example/video_2', voiceover=cls.voiceover1, content_unit=content2
        )
        cls.ser_resource3 = VideoResource.objects.create(
            iframe='http://example/video_3', voiceover=cls.voiceover1, content_unit=content3
        )
        cls.ser_resource4 = VideoResource.objects.create(
            iframe='http://example/video_4', voiceover=cls.voiceover1, content_unit=content4
        )
        cls.ser_resource5 = VideoResource.objects.create(
            iframe='http://example/video_5', voiceover=cls.voiceover2, content_unit=content1
        )
        cls.ser_resource6 = VideoResource.objects.create(
            iframe='http://example/video_6', voiceover=cls.voiceover2, content_unit=content2
        )
        cls.ser_resource7 = VideoResource.objects.create(
            iframe='http://example/video_7', voiceover=cls.voiceover2, content_unit=content3
        )
        cls.ser_resource8 = VideoResource.objects.create(
            iframe='http://example/video_8', voiceover=cls.voiceover2, content_unit=content4
        )

        cls.movie = Title.objects.create(name='Movie', type=Title.MOVIE)
        content = SeasonsInfo.objects.create(title=cls.movie)

        cls.mov_resource1 = VideoResource.objects.create(
            iframe='http://example/video_1', voiceover=cls.voiceover1, content_unit=content
        )
        cls.mov_resource2 = VideoResource.objects.create(
            iframe='http://example/video_2', voiceover=cls.voiceover2, content_unit=content
        )

    def setUp(self):
        self.username = 'test999'
        self.password = '12345'
        self.user = User.objects.create_user(username=self.username, password=self.password, id=999)


class TestHistorySetUpMixin:
    def setUp(self):
        self.username = 'test999'
        self.password = '123456'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        user = User.objects.create_user(username='test1', password=self.password)
        self._create_test_data(1, 5, self.user)
        self._create_test_data(6, 10, user)

    @staticmethod
    def _create_test_data(id_from, id_to, user):
        titles = [Title(name=f'Title {i}', type=Title.MOVIE, id=i) for i in range(id_from, id_to + 1)]
        Title.objects.bulk_create(titles)

        contents = [SeasonsInfo(title=title, id=title.id) for title in titles]
        SeasonsInfo.objects.bulk_create(contents)

        resources = [
            VideoResource(iframe=f'http://video_{content.title_id}', content_unit=content, id=content.id)
            for content in contents
        ]
        VideoResource.objects.bulk_create(resources)

        history = [ViewingHistory(user=user, position=1, resource=resource, id=resource.id) for resource in resources]
        ViewingHistory.objects.bulk_create(history)


@override_settings(MEDIA_ROOT=settings.TEMP_DIR)
def create_image(name, resolution=(100, 100), mb=None, save=False):
    if mb:
        bytes_target = mb * 1024 * 1024
        channels = 3

        pixels = bytes_target // channels
        side = int(pixels**0.5)

        arr = np.random.randint(0, 256, (side, side, channels), dtype=np.uint8)

        image = Image.fromarray(arr, 'RGB')
    else:
        image = Image.new('RGB', resolution, color='red')

    buffer = BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    uploaded_image = SimpleUploadedFile(name=f'{name}.jpg', content=buffer.read(), content_type='image/jpeg')
    if save:
        relative = default_storage.save(f'{settings.TEMP_DIR}/{name}.jpg', uploaded_image)
        return default_storage.path(relative)

    return uploaded_image
