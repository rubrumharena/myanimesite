import itertools
from itertools import chain
from unittest.mock import MagicMock, patch, call, ANY

from django.test import TestCase
from django.utils import timezone

from services.kinopoisk_api import KinopoiskData
from services.utils import generate_episode_structure, update_statistics, update_posters, update_titles
from titles.models import Group, Person, Poster, SeasonsInfo, Studio, Title, Statistic


class GenerateEpisodeStructure(TestCase):
    def test_links_episodes(self):
        title = Title.objects.create(name='Title')
        episodes = 10
        seasons_info = [
            {'number': 1, 'episodesCount': episodes},
            {'number': 2, 'episodesCount': episodes},
        ]

        actual = generate_episode_structure(seasons_info, title)
        expected = []
        for season in seasons_info:
            for episode in range(1, season['episodesCount'] + 1):
                expected.append(SeasonsInfo(title=title, episode=episode, season=season['number']))
        self.assertEqual(
            [(s.season, s.episode, s.title_id) for s in actual],
            [(s.season, s.episode, s.title_id) for s in expected],
        )


class UpdateStatisticsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        titles = [Title(name=f'Title_{i}', kinopoisk_id=i) for i in range(10)]
        Title.objects.bulk_create(titles)
        statistics = [Statistic(kp_rating=7, kp_votes=100, imdb_rating=8, imdb_votes=200, title=title) for title in titles]
        Statistic.objects.bulk_create(statistics)

    def test_happy_path(self):
        titles = Title.objects.all()
        new_ratings = {'kp': 7, 'imdb': 8}
        new_votes = {'kp': 100, 'imdb': 200}
        kp_data = [MagicMock(ratings=new_ratings, votes=new_votes, title_id=title.kinopoisk_id) for title in titles]

        update_statistics(titles, kp_data)

        with self.subTest():
            for title in Title.objects.all():
                self.assertEqual(title.statistic.kp_rating, new_ratings['kp'])
                self.assertEqual(title.statistic.imdb_rating, new_ratings['imdb'])
                self.assertEqual(title.statistic.kp_votes, new_votes['kp'])
                self.assertEqual(title.statistic.imdb_votes, new_votes['imdb'])

    def test_when_kp_data_is_bigger_than_titles(self):
        titles = Title.objects.all()
        new_ratings = {'kp': 7, 'imdb': 8}
        new_votes = {'kp': 100, 'imdb': 200}
        kp_data = [MagicMock(ratings=new_ratings, votes=new_votes, title_id=title.kinopoisk_id) for title in titles]
        kp_data.append(MagicMock(ratings=new_ratings, votes=new_votes, title_id=9999))

        update_statistics(titles, kp_data)

        with self.subTest():
            for title in Title.objects.all():
                self.assertEqual(title.statistic.kp_rating, new_ratings['kp'])
                self.assertEqual(title.statistic.imdb_rating, new_ratings['imdb'])
                self.assertEqual(title.statistic.kp_votes, new_votes['kp'])
                self.assertEqual(title.statistic.imdb_votes, new_votes['imdb'])


class UpdatePostersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        titles = [Title(name=f'Title_{i}', kinopoisk_id=i) for i in range(10)]
        Title.objects.bulk_create(titles)

        posters = [Poster(title=title) for title in titles]
        Poster.objects.bulk_create(posters)

    @patch('services.utils.Poster.build')
    def test_happy_path(self, mock_build):
        titles = Title.objects.all()
        kp_data = [MagicMock(poster=f'url_{title.id}', title_id=title.kinopoisk_id) for title in titles]
        expected_calls = [call(obj.poster, ANY) for obj in kp_data]

        update_posters(titles, kp_data)

        self.assertEqual(mock_build.call_count, titles.count())
        mock_build.assert_has_calls(expected_calls, any_order=True)

    @patch('services.utils.Poster.build')
    def test_when_kp_data_does_not_have_poster(self, mock_build):
        titles = Title.objects.all()
        kp_data = [MagicMock(poster=f'url_{title.id}', title_id=title.kinopoisk_id) for title in titles]
        expected_calls = [call(obj.poster, ANY) for obj in kp_data]
        kp_data.append(MagicMock(poster=None, title_id=titles.first().kinopoisk_id))

        update_posters(titles, kp_data)

        self.assertEqual(mock_build.call_count, titles.count())
        mock_build.assert_has_calls(expected_calls, any_order=True)

    @patch('services.utils.Poster.build')
    def test_when_poster_map_does_not_have_poster(self, mock_build):
        titles = Title.objects.all()
        kp_data = [MagicMock(poster=f'url_{title.id}', title_id=title.kinopoisk_id) for title in titles]
        expected_calls = [call(obj.poster, ANY) for obj in kp_data]
        titles.first().poster.delete()

        update_posters(titles, kp_data)

        self.assertEqual(mock_build.call_count, titles.count())
        mock_build.assert_has_calls(expected_calls, any_order=True)

    @patch('services.utils.Poster.build')
    def test_when_title_does_not_exist(self, mock_build):
        titles = Title.objects.all()
        kp_data = [MagicMock(poster=f'url_{title.id}', title_id=title.kinopoisk_id) for title in titles]
        to_delete = titles.first()
        expected_calls = [call(obj.poster, ANY) for obj in kp_data if obj.title_id != to_delete.kinopoisk_id]
        to_delete.delete()

        update_posters(titles, kp_data)

        self.assertEqual(mock_build.call_count, titles.count() - 1)
        mock_build.assert_has_calls(expected_calls, any_order=True)



class UpdateTitlesTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        titles = [Title(name=f'Title_{i}', kinopoisk_id=i) for i in range(10)]
        Title.objects.bulk_create(titles)
        cls.now = timezone.now()

    @patch('services.utils.timezone.now')
    @patch('services.utils.update_posters')
    @patch('services.utils.update_statistics')
    @patch('services.utils.KinopoiskData')
    @patch('services.utils.KinopoiskClient.get_multiple_info')
    def test_happy_path(self, mock_get_multiple_info, mock_kp_class, mock_update_statistics, mock_update_posters, mock_now):
        titles = Title.objects.all()
        expected_kp_data = [MagicMock(title_id=i) for i in range(10)]

        mock_get_multiple_info.return_value = [MagicMock() for _ in range(10)]
        mock_kp_class.side_effect = expected_kp_data
        mock_now.return_value = self.now

        update_titles(titles)

        mock_update_posters.assert_called_with(titles, expected_kp_data)
        mock_update_statistics.assert_called_with(titles, expected_kp_data)

        for title in Title.objects.all():
            self.assertEqual(title.updated_at, self.now)