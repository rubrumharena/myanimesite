from unittest.mock import patch

from django.test import TestCase

from common.utils.testing_components import TestVideoPlayerSetUpMixin
from titles.models import SeasonsInfo
from video_player.models import VideoResource, ViewingHistory, VoiceOver


class ViewingHistoryModelTestCase(TestVideoPlayerSetUpMixin, TestCase):
    def setUp(self):
        super().setUp()

    def _common_tests(self, actual_data, expected_data):
        self.assertEqual(len(actual_data['seasons']), expected_data['seasons'])
        self.assertEqual(len(actual_data['episodes']), expected_data['episodes'])
        self.assertEqual(actual_data['cur_episode'], expected_data['cur_episode'])
        self.assertEqual(actual_data['cur_season'], expected_data['cur_season'])
        self.assertEqual(actual_data['cur_voiceover_id'], expected_data['cur_voiceover_id'])
        self.assertEqual(actual_data['time'], expected_data['time'])
        self.assertEqual(actual_data['video'], expected_data['video'])
        self.assertEqual(list(actual_data['voiceovers']), list(expected_data['voiceovers']))
        self.assertEqual(actual_data['available_episodes'], expected_data['available_episodes'])
        self.assertEqual(actual_data['available_seasons'], expected_data['available_seasons'])

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_when_record_is_empty(self, mock_cache_get, mock_cache_set):
        record = ViewingHistory()
        resource = VideoResource.objects.first()
        actual_data = record._build_track_info(resource)
        base_q = VideoResource.objects.filter(
            content_unit__title=resource.content_unit.title, voiceover=resource.voiceover
        )

        voiceover_ids = VideoResource.objects.filter(
            content_unit=resource.content_unit, voiceover__isnull=False
        ).values_list('voiceover_id', flat=True)

        expected_data = {
            'seasons': base_q.values('content_unit__season').distinct().count(),
            'episodes': base_q.filter(content_unit__season=resource.content_unit.season).count(),
            'cur_episode': 1,
            'cur_season': 1,
            'cur_voiceover_id': resource.voiceover_id,
            'time': 0,
            'video': resource.iframe,
            'voiceovers': VoiceOver.objects.filter(id__in=voiceover_ids),
            'available_episodes': list(
                base_q.filter(content_unit__season=resource.content_unit.season).values_list(
                    'content_unit__episode', flat=True
                )
            ),
            'available_seasons': list(base_q.distinct().values_list('content_unit__season', flat=True)),
        }
        self._common_tests(actual_data, expected_data)

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_when_record_exists(self, mock_cache_get, mock_cache_set):
        cur_season = 2
        cur_episode = 2
        resource = VideoResource.objects.filter(
            content_unit__season=cur_season, content_unit__episode=cur_episode
        ).first()
        record = ViewingHistory.objects.create(user=self.user, resource=resource)
        base_q = VideoResource.objects.filter(
            content_unit__title=resource.content_unit.title, voiceover=resource.voiceover
        )

        voiceover_ids = VideoResource.objects.filter(
            content_unit=resource.content_unit, voiceover__isnull=False
        ).values_list('voiceover_id', flat=True)

        actual_data = record._build_track_info(resource)
        expected_data = {
            'seasons': base_q.values('content_unit__season').distinct().count(),
            'episodes': base_q.filter(content_unit__season=resource.content_unit.season).count(),
            'cur_episode': cur_season,
            'cur_season': cur_episode,
            'cur_voiceover_id': resource.voiceover_id,
            'time': 0,
            'video': resource.iframe,
            'voiceovers': VoiceOver.objects.filter(id__in=voiceover_ids),
            'available_episodes': list(
                base_q.filter(content_unit__season=resource.content_unit.season).values_list(
                    'content_unit__episode', flat=True
                )
            ),
            'available_seasons': list(base_q.distinct().values_list('content_unit__season', flat=True)),
        }
        self._common_tests(actual_data, expected_data)

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_if_title_is_movie(self, mock_cache_get, mock_cache_set):
        record = ViewingHistory()
        resource = VideoResource.objects.filter(content_unit__title=self.movie).first()

        voiceover_ids = VideoResource.objects.filter(
            content_unit=resource.content_unit, voiceover__isnull=False
        ).values_list('voiceover_id', flat=True)

        actual_data = record._build_track_info(resource)
        expected_data = {
            'seasons': 0,
            'episodes': 0,
            'cur_episode': None,
            'cur_season': None,
            'cur_voiceover_id': resource.voiceover_id,
            'time': 0,
            'video': resource.iframe,
            'voiceovers': VoiceOver.objects.filter(id__in=voiceover_ids),
            'available_episodes': [],
            'available_seasons': [],
        }
        self._common_tests(actual_data, expected_data)

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_if_the_first_season_is_zero(self, mock_cache_get, mock_cache_set):
        season_info = SeasonsInfo.objects.create(season=0, episode=1, title=self.series)
        resource = VideoResource.objects.create(
            content_unit=season_info, voiceover=VoiceOver.objects.first(), iframe='http://example/video_0'
        )
        record = ViewingHistory.objects.create(user=self.user, resource=resource)
        base_q = VideoResource.objects.filter(
            content_unit__title=resource.content_unit.title, voiceover=resource.voiceover
        )

        voiceover_ids = VideoResource.objects.filter(
            content_unit=resource.content_unit, voiceover__isnull=False
        ).values_list('voiceover_id', flat=True)

        actual_data = record._build_track_info(resource)
        expected_data = {
            'seasons': base_q.values('content_unit__season').distinct().count(),
            'episodes': base_q.filter(content_unit__season=resource.content_unit.season).count(),
            'cur_episode': 1,
            'cur_season': 0,
            'cur_voiceover_id': resource.voiceover_id,
            'time': 0,
            'video': resource.iframe,
            'voiceovers': VoiceOver.objects.filter(id__in=voiceover_ids),
            'available_episodes': list(
                base_q.filter(content_unit__season=resource.content_unit.season).values_list(
                    'content_unit__episode', flat=True
                )
            ),
            'available_seasons': list(base_q.distinct().values_list('content_unit__season', flat=True)),
        }
        self._common_tests(actual_data, expected_data)
