from Tools.scripts.objgraph import flat
from django.test import TestCase

from common.utils.testing_components import TestVideoPlayerSetUpMixin
from titles.models import Title, SeasonsInfo
from users.models import User
from video_player.models import ViewingHistory, VoiceOver, VideoResource


class TitleGetWatchingDataTestCase(TestVideoPlayerSetUpMixin, TestCase):

    def setUp(self):
        super().setUp()


    def _common_tests(self, actual_data, expected_data):
        self.assertEqual(len(actual_data['seasons']), expected_data['seasons'])
        self.assertEqual(len(list(actual_data['episodes'])), expected_data['episodes'])
        self.assertEqual(actual_data['cur_episode'], expected_data['cur_episode'])
        self.assertEqual(actual_data['cur_season'], expected_data['cur_season'])
        self.assertEqual(actual_data['cur_voiceover'], expected_data['cur_voiceover'])
        self.assertEqual(actual_data['time'], expected_data['time'])
        self.assertEqual(actual_data['video'], expected_data['video'])
        self.assertEqual(actual_data['voiceovers'], expected_data['voiceovers'])
        self.assertEqual(actual_data['available_episodes'], expected_data['available_episodes'])
        self.assertEqual(actual_data['available_seasons'], expected_data['available_seasons'])

    def test_when_record_is_empty(self):
        record = ViewingHistory()
        resource = VideoResource.objects.first()
        actual_data = record.get_track_info(resource)
        base_q = VideoResource.objects.filter(content_unit__title=resource.content_unit.title, voiceover=resource.voiceover)

        expected_data = {
            'seasons': base_q.values('content_unit__season').distinct().count(),
            'episodes': base_q.filter(content_unit__season=resource.content_unit.season).count(),
            'cur_episode': 1,
            'cur_season': 1,
            'cur_voiceover': resource.voiceover_id,
            'time': 0,
            'video': resource.iframe,
            'voiceovers': list(VideoResource.objects.filter(content_unit=resource.content_unit,
                                                                       voiceover__isnull=False).values('voiceover_id', 'voiceover__name')),
            'available_episodes': list(base_q.filter(content_unit__season=resource.content_unit.season).values_list('content_unit__episode', flat=True)),
            'available_seasons': list(base_q.distinct().values_list('content_unit__season', flat=True))
        }
        self._common_tests(actual_data, expected_data)

    def test_when_record_exists(self):
        cur_season = 2
        cur_episode = 2
        resource = VideoResource.objects.filter(content_unit__season=cur_season, content_unit__episode=cur_episode).first()
        record = ViewingHistory.objects.create(user=self.user, resource=resource)
        base_q = VideoResource.objects.filter(content_unit__title=resource.content_unit.title,
                                              voiceover=resource.voiceover)

        actual_data = record.get_track_info()
        expected_data = {
            'seasons': base_q.values('content_unit__season').distinct().count(),
            'episodes': base_q.filter(content_unit__season=resource.content_unit.season).count(),
            'cur_episode': cur_season,
            'cur_season': cur_episode,
            'cur_voiceover': resource.voiceover_id,
            'time': 0,
            'video': resource.iframe,
            'voiceovers': list(VideoResource.objects.filter(content_unit=resource.content_unit,
                                                                       voiceover__isnull=False).values('voiceover_id', 'voiceover__name')),
            'available_episodes': list(base_q.filter(content_unit__season=resource.content_unit.season).values_list('content_unit__episode', flat=True)),
            'available_seasons': list(base_q.distinct().values_list('content_unit__season', flat=True))
        }
        self._common_tests(actual_data, expected_data)

    def test_if_title_is_movie(self):
        record = ViewingHistory()
        resource = VideoResource.objects.filter(content_unit__title=self.movie).first()

        actual_data = record.get_track_info(resource)
        expected_data = {
            'seasons': 0,
            'episodes': 0,
            'cur_episode': None,
            'cur_season': None,
            'cur_voiceover': resource.voiceover_id,
            'time': 0,
            'video': resource.iframe,
            'voiceovers': list(VideoResource.objects.filter(content_unit=resource.content_unit,
                                                                       voiceover__isnull=False).values('voiceover_id', 'voiceover__name')),
            'available_episodes': [],
            'available_seasons': []
        }
        self._common_tests(actual_data, expected_data)

    def test_if_the_first_season_is_zero(self):
        season_info = SeasonsInfo.objects.create(season=0, episode=1, title=self.series)
        resource = VideoResource.objects.create(content_unit=season_info, voiceover=VoiceOver.objects.first(), iframe=f'http://example/video_0')
        record = ViewingHistory.objects.create(user=self.user, resource=resource)
        base_q = VideoResource.objects.filter(content_unit__title=resource.content_unit.title,
                                              voiceover=resource.voiceover)

        actual_data = record.get_track_info()
        expected_data = {
            'seasons': base_q.values('content_unit__season').distinct().count(),
            'episodes': base_q.filter(content_unit__season=resource.content_unit.season).count(),
            'cur_episode': 1,
            'cur_season': 0,
            'cur_voiceover': resource.voiceover_id,
            'time': 0,
            'video': resource.iframe,
            'voiceovers': list(VideoResource.objects.filter(content_unit=resource.content_unit,
                                                                       voiceover__isnull=False).values('voiceover_id', 'voiceover__name')),
            'available_episodes': list(base_q.filter(content_unit__season=resource.content_unit.season).values_list('content_unit__episode', flat=True)),
            'available_seasons': list(base_q.distinct().values_list('content_unit__season', flat=True))
        }
        self._common_tests(actual_data, expected_data)

    def test_if_no_resources(self):
        title = Title.objects.create(name='New Title', type=Title.SERIES)

        season = (SeasonsInfo(episode=i, season=1, title=title) for i in range(1, 6))
        SeasonsInfo.objects.bulk_create(season)
        record = ViewingHistory()

        actual_data = record.get_track_info(title=title)
        expected_data = {
            'seasons': 1,
            'episodes': 5,
            'cur_episode': None,
            'cur_season': 1,
            'cur_voiceover': None,
            'time': 0,
            'video': None,
            'voiceovers': [],
            'available_episodes': [],
            'available_seasons': []
        }
        self._common_tests(actual_data, expected_data)

    def test_if_no_season_info(self):
        title = Title.objects.create(name='New Title', type=Title.SERIES)

        record = ViewingHistory()
        actual_data = record.get_track_info(title=title)

        expected_data = {
            'seasons': 0,
            'episodes': 0,
            'cur_episode': None,
            'cur_season': None,
            'cur_voiceover': None,
            'time': 0,
            'video': None,
            'voiceovers': [],
            'available_episodes': [],
            'available_seasons': []
        }
        self._common_tests(actual_data, expected_data)

    def test_if_no_record_resource_or_title_were_given(self):
        record = ViewingHistory()
        with self.assertRaises(ValueError) as _:
            record.get_track_info()
