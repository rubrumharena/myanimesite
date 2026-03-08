import itertools
from itertools import chain
from unittest.mock import MagicMock, patch

from django.test import TestCase

from common.utils.testing_components import TestJoinMixin
from lists.models import Collection
from services.kinopoisk_import import (
    join_persons,
    join_sequels_and_prequels,
    join_studios,
)
from services.kinopoisk_joiners import generate_episode_structure, join_genres
from services.tasks import load_posters
from titles.models import Group, Person, Poster, SeasonsInfo, Studio, Title


class JoinSequelsAndPrequelsTestCase(TestCase):
    def _common_tests(self, expected_data, excluded_ids=None):
        excluded_ids = [] if excluded_ids is None else excluded_ids

        self.assertEqual(Group.objects.count(), len(list(chain.from_iterable(expected_data.values()))))
        for parent, children in expected_data.items():
            self.assertFalse(Group.objects.filter(parent_id=parent, child_id=parent).exists())
            for child in children:
                if excluded_ids and child in excluded_ids:
                    self.assertFalse(Group.objects.filter(parent_id=parent, child_id=child).exists())
                    continue
                self.assertTrue(Group.objects.filter(parent_id=parent, child_id=child).exists())

    def test_join_sequels_and_prequels_when_title_model_fully_loaded(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        groups = {1: [2, 3], 2: [1, 3], 3: [1, 2], 4: [], 5: []}

        join_sequels_and_prequels(groups)

        self._common_tests(groups)

    def test_join_sequels_and_prequels_when_there_are_no_certain_titles_in_db(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        groups = {1: [2, 3], 2: [1, 3], 3: [1, 2, 6], 4: [], 5: []}
        expected_data = {1: [2, 3], 2: [1, 3], 3: [1, 2], 4: [], 5: []}

        join_sequels_and_prequels(groups)

        self._common_tests(expected_data, excluded_ids=[6])

    def test_join_sequels_and_prequels_when_there_are_some_different_groups(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 9)]
        Title.objects.bulk_create(titles)
        groups = {1: [2, 3], 2: [1], 3: [1, 2], 4: [5, 9], 5: [9], 7: [8], 8: []}
        expected_data = {1: [2, 3], 2: [1, 3], 3: [1, 2], 4: [5], 5: [4], 7: [8], 8: [7]}

        join_sequels_and_prequels(groups)

        self._common_tests(expected_data, excluded_ids=[9])

    def test_join_sequels_and_prequels_when_they_are_empty(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 4)]
        Title.objects.bulk_create(titles)
        groups = {1: [], 2: [], 3: []}
        expected_data = {1: [], 2: [], 3: []}

        join_sequels_and_prequels(groups)

        self._common_tests(expected_data)

    def test_cyclic_link(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        groups = {1: [2], 2: [3], 3: []}
        expected_data = {1: [2, 3], 2: [1, 3], 3: [1, 2]}

        join_sequels_and_prequels(groups)

        self._common_tests(expected_data)

    def test_should_create_relations_for_existing_ids1(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)

        groups = {1: [2, 3], 2: [1, 3], 3: [1, 2, 4]}
        expected_data = {1: [2, 3, 4], 2: [1, 3, 4], 3: [1, 2, 4], 4: [1, 2, 3]}

        join_sequels_and_prequels(groups)

        self._common_tests(expected_data)

    def test_should_create_relations_for_existing_ids2(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)

        groups = {1: [2, 3, 4]}
        expected_data = {1: [2, 3, 4], 2: [1, 3, 4], 3: [1, 2, 4], 4: [1, 2, 3]}

        join_sequels_and_prequels(groups)

        self._common_tests(expected_data)

    def test_should_not_create_existing_group_relations(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        Group.objects.bulk_create(
            [Group(parent_id=4, child_id=1), Group(parent_id=4, child_id=2), Group(parent_id=4, child_id=3)]
        )

        groups = {1: [2, 3], 2: [1, 3], 3: [1, 2, 4]}
        expected_data = {1: [2, 3, 4], 2: [1, 3, 4], 3: [1, 2, 4], 4: [1, 2, 3]}

        join_sequels_and_prequels(groups)

        self._common_tests(expected_data)


class JoinStudiosTestCase(TestJoinMixin, TestCase):
    def setUp(self):
        self.related_model = Title.studios.through
        self.model = Studio
        self.related_field = 'studio__name'

    def test_join_studios_creates_relations(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        studios = {1: ['Studio 1', 'Studio 2'], 2: ['Studio 3'], 3: [], 4: [], 5: []}

        join_studios(studios)

        self._common_tests(studios)

    def test_same_studio_linked_to_multiple_titles(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        studios = {1: ['Studio 1'], 2: ['Studio 1'], 3: ['Studio 1'], 4: [], 5: []}

        join_studios(studios)

        self._common_tests(studios)

    def test_when_some_studios_are_in_db(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        studios_before = {1: ['Studio 1'], 2: ['Studio 2']}
        studios_after = {3: ['Studio 1'], 4: ['Studio 2', 'Studio 3']}

        join_studios(studios_before)
        join_studios(studios_after)

        studios_after.update(studios_before)
        self._common_tests(studios_after)

    def test_same_genres_linked_to_one_title(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        studios = {1: ['Studio 1', 'Studio 2'], 2: ['Studio 3', 'Studio 3'], 3: [], 4: [], 5: []}

        join_studios(studios)

        self.assertEqual(self.related_model.objects.count(), 3)
        self._common_tests(studios, miss_links=True)


class JoinPersonsTestCase(TestJoinMixin, TestCase):
    def setUp(self):
        self.related_model = Title.persons.through
        self.model = Person
        self.related_field = 'person__kinopoisk_id'
        self.data_count, self.title_count, self.step = None, None, None

    @staticmethod
    def _clean_data(data):
        cleaned_data = {title_id: [] for title_id in data}
        for title_id, persons in data.items():
            for person in persons:
                cleaned_data[title_id].append(person['id'])
        return cleaned_data

    def _prepare_persons(self, data):
        persons = {}
        for i in range(0, self.data_count + 1, self.step):
            persons[self.title_count] = data[i : i + self.step]
            self.title_count -= 1
        return persons

    def _prepare_test_data(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, self.title_count + 1)]
        Title.objects.bulk_create(titles)

        data_from_api = [
            {
                'id': i,
                'name': f'Name {i}',
                'description': 'Something',
                'enProfession': 'actor',
                'photo': f'https://www.example.com/{i}',
            }
            for i in range(1, self.data_count + 1)
        ]

        return self._prepare_persons(data_from_api)

    def test_join_persons_creates_relations(self):
        self.title_count = 2
        self.data_count = 20
        self.step = 10

        persons = self._prepare_test_data()
        join_persons(persons)
        data = self._clean_data(persons)

        self._common_tests(data)

    def test_same_person_linked_to_multiple_titles(self):
        self.title_count = 5
        self.data_count = 25
        self.step = 5

        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, self.title_count + 1)]
        Title.objects.bulk_create(titles)

        data_from_api = [
            {
                'id': 1,
                'name': 'Name 1',
                'description': 'Something',
                'enProfession': 'actor',
                'photo': 'https://www.example.com/1',
            }
            for i in range(1, self.data_count + 1)
        ]

        persons = self._prepare_persons(data_from_api)
        join_persons(persons)

        data = self._clean_data(persons)
        self.assertEqual(self.related_model.objects.count(), 5)
        self._common_tests(data, miss_links=True)

    def test_when_some_persons_are_in_db(self):
        self.title_count = 5
        self.data_count = 50
        self.step = 10

        persons = self._prepare_test_data()

        persons_before = dict(itertools.islice(persons.items(), 2))
        join_persons(persons_before)
        data = self._clean_data(persons_before)
        self._common_tests(data)

        join_persons(persons)
        data = self._clean_data(persons)
        self._common_tests(data)

    def test_when_incoming_data_is_enormous(self):
        self.title_count = 250
        self.data_count = 10_000
        self.step = 40

        persons = self._prepare_test_data()

        with patch('titles.models.Person.objects.filter', wraps=Person.objects.filter) as mock_filter:
            join_persons(persons)
            self.assertEqual(mock_filter.call_count, 2)

        data = self._clean_data(persons)
        self._common_tests(data)


class JoinGenresTestCase(TestJoinMixin, TestCase):
    def setUp(self):
        self.related_model = Collection.titles.through
        self.model = Collection
        self.related_field = 'collection__name'

    @patch('services.kinopoisk_joiners.enrich_genres')
    def test_join_genres_creates_relations(self, mock_enrich_genres):
        title_count = 5
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, title_count + 1)]
        Title.objects.bulk_create(titles)
        genres = {1: ['Жанр Жанр 1', 'Жанр 2'], 2: ['Жанр 3'], 3: ['Жанр 4'], 4: ['Жанр 5', 'Жанр 6'], 5: ['Жанр 7']}

        join_genres(genres)
        self.assertTrue(Collection.objects.filter(name='Жанр Жанр 1').exists())

    @patch('services.kinopoisk_joiners.enrich_genres')
    def test_same_genres_linked_to_multiple_titles(self, mock_enrich_genres):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        genres = {1: ['Жанр 1'], 2: ['Жанр 1'], 3: ['Жанр 1'], 4: [], 5: []}

        join_genres(genres)

        self._common_tests(genres)

    @patch('services.kinopoisk_joiners.enrich_genres')
    def test_when_some_genres_are_in_db(self, mock_enrich_genres):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        genres_before = {1: ['Жанр 1'], 2: ['Жанр 2']}
        genres_after = {3: ['Жанр 1'], 4: ['Жанр 2', 'Жанр 3']}

        join_genres(genres_before)
        join_genres(genres_after)

        genres_after.update(genres_before)
        self._common_tests(genres_after)

    @patch('services.kinopoisk_joiners.enrich_genres')
    def test_same_genres_linked_to_one_title(self, mock_enrich_genres):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        genres = {1: ['Жанр 1'], 2: ['Жанр 2'], 3: ['Жанр 3', 'Жанр 3'], 4: [], 5: []}

        join_genres(genres)

        self.assertEqual(self.related_model.objects.count(), 3)
        self._common_tests(genres, miss_links=True)


class JoinPostersTestCase(TestJoinMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        titles = [Title(name=f'Title {i}', kinopoisk_id=i) for i in range(1, 6)]
        Title.objects.bulk_create(titles)

    @patch('services.tasks.requests.Session')
    @patch.object(Poster, 'save')
    @patch.object(Poster, 'build')
    def test_happy_path(self, mock_build, mock_save, mock_session):
        mock_session.return_value = MagicMock()
        mock_build.return_value = True

        posters = {str(title.kinopoisk_id): f'url_{title.kinopoisk_id}' for title in Title.objects.all()}

        load_posters(posters)

        self.assertEqual(mock_build.call_count, len(posters))
        self.assertEqual(mock_save.call_count, len(posters))

        for url in posters.values():
            mock_build.assert_any_call(url, mock_session.return_value)

    @patch('services.tasks.requests.Session')
    @patch.object(Poster, 'save')
    @patch.object(Poster, 'build')
    def test_when_build_returns_none(self, mock_build, mock_save, mock_session):
        mock_session.return_value = MagicMock()
        mock_build.side_effect = [False, False, True, True, True]
        posters = {title.kinopoisk_id: f'url_{title.kinopoisk_id}' for title in Title.objects.all()}
        load_posters(posters)

        self.assertEqual(mock_build.call_count, len(posters))
        self.assertEqual(mock_save.call_count, len(posters) - 2)

        with self.subTest():
            for poster in posters.values():
                mock_build.assert_any_call(poster, mock_session.return_value)


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
