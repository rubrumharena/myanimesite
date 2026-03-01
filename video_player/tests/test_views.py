import json
from http import HTTPStatus
from unittest.mock import patch

from django.shortcuts import reverse
from django.test import TestCase

from common.utils.testing_components import TestVideoPlayerSetUpMixin
from common.utils.types import EpisodeTracker
from video_player.models import VideoResource, ViewingHistory


class VideoPlayerAjaxViewGetTestCase(TestVideoPlayerSetUpMixin, TestCase):
    def setUp(self):
        self.path_get = reverse('video_player:get_content', kwargs={'title_id': self.series.id})
        self.test_plug = EpisodeTracker().__dict__

    def _common_tests(self, response):
        context = response.context
        data = json.loads(response.content)
        self.assertTemplateUsed(response, 'video_player/video_player.html')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(context['tracker'], self.test_plug)
        self.assertTrue(data['html'])

    @patch('video_player.views.ViewingHistory.get_independent_info')
    @patch('video_player.views.VideoResource.objects.get_fallback')
    def test_when_no_params(self, mock_get_fallback, mock_get_track_info):
        self.client.login(username=self.username, password=self.password)

        mock_get_track_info.return_value = self.test_plug
        mock_get_fallback.return_value = self.ser_resource1

        response = self.client.get(self.path_get)

        mock_get_fallback.assert_called_once_with(title=self.series, user=self.user)
        mock_get_track_info.assert_called_once_with(self.ser_resource1)
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_user_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_user_has_record(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug
        ViewingHistory.objects.create(user=self.user, resource=self.ser_resource1)

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path_get)

        mock_get_track_info.assert_called_once()
        mock_get_fallback.assert_not_called()
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_user_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_user_has_several_records_for_one_title(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug
        ViewingHistory.objects.create(user=self.user, resource=self.ser_resource1)
        ViewingHistory.objects.create(user=self.user, resource=self.ser_resource2)

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path_get)

        mock_get_track_info.assert_called_once()
        mock_get_fallback.assert_not_called()
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_independent_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_when_title_is_movie(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(
            reverse('video_player:get_content', kwargs={'title_id': self.movie.id})
            + f'?voiceover_id={self.voiceover2.id}'
        )

        mock_get_track_info.assert_called_with(self.mov_resource2)
        mock_get_fallback.assert_not_called()
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_independent_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_clicked_on_episode(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(self.path_get + f'?voiceover_id={self.voiceover2.id}&episode=2&season=2')

        mock_get_track_info.assert_called_with(self.ser_resource8)
        mock_get_fallback.assert_not_called()
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_independent_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_clicked_on_season(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(self.path_get + f'?voiceover_id={self.voiceover2.id}&season=2')

        mock_get_track_info.assert_called_with(self.ser_resource7)
        mock_get_fallback.assert_not_called()
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_independent_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_clicked_on_voiceover(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(self.path_get + f'?voiceover_id={self.voiceover2.id}')

        mock_get_track_info.assert_called_with(self.ser_resource5)
        mock_get_fallback.assert_not_called()
        self._common_tests(response)


class VideoPlayerAjaxViewPostTestCase(TestVideoPlayerSetUpMixin, TestCase):
    def setUp(self):
        ViewingHistory.objects.create(user=self.user, resource=self.ser_resource1, position=10)
        self.base_data = {
            'position': 10,
            'season': self.ser_resource1.content_unit.season,
            'episode': self.ser_resource1.content_unit.episode,
            'voiceover_id': self.ser_resource1.voiceover.id,
        }
        self.path_post = reverse('video_player:save_progress', kwargs={'title_id': self.series.id})

    def test_when_user_is_not_authenticated(self):
        response = self.client.post(self.path_post, {})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_when_no_resources(self):
        resources = VideoResource.objects.all()
        resources.delete()

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path_post, self.base_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_when_no_prev_records(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path_post, self.base_data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(ViewingHistory.objects.first().position, self.base_data['position'])

    def test_when_user_has_some_records_from_one_season(self):
        ViewingHistory.objects.create(user=self.user, resource=self.ser_resource2, position=20)

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path_post, self.base_data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(ViewingHistory.objects.last().position, 20)

    def test_when_title_is_movie(self):
        self.base_data['episode'] = ''
        self.base_data['season'] = ''
        content = self.ser_resource1.content_unit
        content.season = None
        content.episode = None
        content.save()

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path_post, self.base_data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(ViewingHistory.objects.first().position, self.base_data['position'])

    def test_invalid_cases(self):
        test_cases = [
            {
                'position': -10,
                'season': self.ser_resource1.content_unit.season,
                'episode': self.ser_resource1.content_unit.episode,
                'voiceover_id': self.ser_resource1.voiceover.id,
            },
            {
                'position': 10,
                'season': 'test',
                'episode': self.ser_resource1.content_unit.episode,
                'voiceover_id': self.ser_resource1.voiceover.id,
            },
            {
                'position': 10,
                'season': self.ser_resource1.content_unit.season,
                'episode': 'test',
                'voiceover_id': self.ser_resource1.voiceover.id,
            },
        ]

        self.client.login(username=self.username, password=self.password)

        for case in test_cases:
            with self.subTest(case=case):
                response = self.client.post(self.path_post, case)
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
