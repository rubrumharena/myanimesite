import json
from http import HTTPStatus
from unittest.mock import patch

from django.test import TestCase
from django.shortcuts import reverse

from common.utils.testing_components import TestVideoPlayerSetUpMixin
from common.utils.enums import EpisodeTracker
from titles.models import SeasonsInfo, Title
from video_player.models import VideoResource, ViewingHistory, VoiceOver


class VideoPlayerAjaxViewGETTestCase(TestVideoPlayerSetUpMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.path_get = reverse('video_player:get_video_content_ajax', kwargs={'title_id': self.series.id})
        self.test_plug = EpisodeTracker().__dict__

    def _common_tests(self, response):
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(json.loads(response.content.decode()), self.test_plug)

    @patch('video_player.views.ViewingHistory.get_track_info')
    @patch('video_player.views.VideoResource.objects.get_fallback')
    def test_when_no_params(self, mock_get_fallback, mock_get_track_info):
        self.client.login(username=self.username, password=self.password)

        mock_get_track_info.return_value = self.test_plug
        mock_get_fallback.return_value = self.ser_resource1

        response = self.client.get(self.path_get)

        mock_get_fallback.assert_called_once_with(title=self.series, user=self.user)
        mock_get_track_info.assert_called_once_with(self.ser_resource1, self.series)
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_track_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_user_has_record(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug
        ViewingHistory.objects.create(user=self.user, resource=self.ser_resource1)

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path_get)

        mock_get_track_info.assert_called_once()
        mock_get_fallback.assert_not_called()
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_track_info')
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

    @patch('video_player.views.ViewingHistory.get_track_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_when_title_is_movie(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('video_player:get_video_content_ajax', kwargs={'title_id': self.movie.id}) +
                                   f'?voiceover={self.voiceover2.id}')

        mock_get_track_info.assert_called_with(self.mov_resource2, self.movie)
        mock_get_fallback.assert_not_called()
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_track_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_clicked_on_episode(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(self.path_get + f'?voiceover={self.voiceover2.id}&episode=2&season=2')

        mock_get_track_info.assert_called_with(self.ser_resource8, self.series)
        mock_get_fallback.assert_not_called()
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_track_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_clicked_on_season(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(self.path_get + f'?voiceover={self.voiceover2.id}&season=2')

        mock_get_track_info.assert_called_with(self.ser_resource7, self.series)
        mock_get_fallback.assert_not_called()
        self._common_tests(response)

    @patch('video_player.views.ViewingHistory.get_track_info')
    @patch('video_player.views.VideoResource.objects.get_fallback', return_value=None)
    def test_clicked_on_voiceover(self, mock_get_fallback, mock_get_track_info):
        mock_get_track_info.return_value = self.test_plug
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(self.path_get + f'?voiceover={self.voiceover2.id}')

        mock_get_track_info.assert_called_with(self.ser_resource5, self.series)
        mock_get_fallback.assert_not_called()
        self._common_tests(response)


class VideoPlayerAjaxViewPOSTTestCase(TestVideoPlayerSetUpMixin, TestCase):

    def setUp(self):
        super().setUp()
        ViewingHistory.objects.create(user=self.user, resource=self.ser_resource1, position=10)
        self.base_data = {'title_id': self.series.id, 'position': 10,
                          'season': self.ser_resource1.content_unit.season,
                          'episode': self.ser_resource1.content_unit.episode,
                          'voiceover': self.ser_resource1.voiceover.id}
        self.path_post = reverse('video_player:save_watching_info_ajax')

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
            {'title_id': self.series.id, 'position': -10,
             'season': self.ser_resource1.content_unit.season, 'episode': self.ser_resource1.content_unit.episode,
             'voiceover_id': self.ser_resource1.voiceover.id},
            {'title_id': self.series.id, 'position': 10,
             'season': 'test', 'episode': self.ser_resource1.content_unit.episode,
             'voiceover_id': self.ser_resource1.voiceover.id},
            {'title_id': self.series.id, 'position': 10,
             'season': self.ser_resource1.content_unit.season, 'episode': 'test',
             'voiceover_id': self.ser_resource1.voiceover.id}
        ]

        self.client.login(username=self.username, password=self.password)

        for case in test_cases:
            with self.subTest(case=case):
                response = self.client.post(self.path_post, case)
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
