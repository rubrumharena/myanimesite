import itertools
import json
from itertools import chain, zip_longest
from unittest.mock import patch

from django.test import TestCase, override_settings

from common.utils.testing_components import TestJoinMixin
from lists.models import Collection
from services.kinopoisk_import import (
    create_movie_objs,
    data_initialization,
    join_genres,
    join_persons,
    join_sequels_and_prequels,
    join_studios,
)
from titles.models import Backdrop, Group, Person, Poster, SeasonsInfo, Statistic, Studio, Title


class DataInitializationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        with open('services/fixtures/first_batch.json', encoding='utf-8') as file:
            cls.parent_data = json.load(file)

        with open('services/fixtures/second_batch.json', encoding='utf-8') as file:
            cls.child_data = json.load(file)

    def setUp(self):
        self.base_configuration = {
            'page': 2,
            'limit': 1,
            'rating': '1-10',
            'is_series': '',
            'year': '',
            'genre': '',
            'sequels': False,
        }

    @patch('services.kinopoisk_api.KinopoiskClient.get_multiple_info')
    def test_returns_original_and_sequels_if_sequels_enabled(self, mock_api_call):
        mock_api_call.side_effect = [self.parent_data, self.child_data]
        expected_ids = {obj['id'] for obj in self.parent_data + self.child_data}

        self.base_configuration['sequels'] = True
        titles, title_ids = data_initialization(self.base_configuration)

        self.assertEqual(mock_api_call.call_count, 2)
        self.assertEqual(len(titles), len(expected_ids))
        self.assertEqual(len(title_ids), len(expected_ids))

    @patch('services.kinopoisk_api.KinopoiskClient.get_multiple_info')
    def test_data_initialization_returns_only_originals_if_sequels_enabled_but_empty(self, mock_api_call):
        mock_api_call.return_value = self.parent_data
        expected_ids = {obj['id'] for obj in self.parent_data}

        for title in self.parent_data:
            title['sequelsAndPrequels'] = []

        self.base_configuration['sequels'] = True
        titles, title_ids = data_initialization(self.base_configuration)

        self.assertEqual(mock_api_call.call_count, 1)
        self.assertEqual(len(titles), len(expected_ids))
        self.assertEqual(len(title_ids), len(expected_ids))

    @patch('services.kinopoisk_api.KinopoiskClient.get_multiple_info')
    def test_base_data_initialization(self, mock_api_call):
        mock_api_call.return_value = self.parent_data
        expected_ids = {obj['id'] for obj in self.parent_data}

        titles, title_ids = data_initialization(self.base_configuration)

        self.assertEqual(mock_api_call.call_count, 1)
        self.assertEqual(len(titles), len(expected_ids))
        self.assertEqual(len(title_ids), len(expected_ids))

    @patch('services.kinopoisk_api.KinopoiskClient.get_multiple_info')
    def test_data_initialization_includes_sequels_from_initial_response_when_enabled(self, mock_api_call):
        for title in self.child_data:
            title['sequelsAndPrequels'] = []
        united_data = self.child_data + self.parent_data
        expected_ids = {obj['id'] for obj in united_data}
        mock_api_call.return_value = united_data

        self.base_configuration['sequels'] = True
        titles, title_ids = list(data_initialization(self.base_configuration))
        self.assertEqual(mock_api_call.call_count, 1)
        self.assertEqual(len(titles), len(expected_ids))
        self.assertEqual(len(title_ids), len(expected_ids))

    @patch('services.kinopoisk_api.KinopoiskClient.get_multiple_info')
    def test_data_initialization_when_some_titles_are_in_db(self, mock_api_call):
        title1 = self.parent_data[0]
        title2 = self.child_data[0]
        db_titles = [
            Title(kinopoisk_id=title1['id'], name=title1['name']),
            Title(kinopoisk_id=title2['id'], name=title2['name']),
        ]
        Title.objects.bulk_create(db_titles)

        expected_ids = {
            title['id']
            for title in self.parent_data + self.child_data
            if title['id'] not in [title1['id'], title2['id']]
        }
        expected_parent_value = [obj for obj in self.parent_data if obj['id'] in expected_ids]
        expected_child_value = [obj for obj in self.child_data if obj['id'] in expected_ids]

        mock_api_call.side_effect = [expected_parent_value, expected_child_value]
        self.base_configuration['sequels'] = True
        titles, title_ids = list(data_initialization(self.base_configuration))

        self.assertEqual(mock_api_call.call_count, 2)
        self.assertEqual(len(titles), len(expected_ids))
        self.assertEqual(len(title_ids), len(expected_ids))


class CreateMovieObjectsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        with open('services/fixtures/first_batch.json', encoding='utf-8') as file:
            cls.parent_data = json.load(file)

        with open('services/fixtures/second_batch.json', encoding='utf-8') as file:
            cls.child_data = json.load(file)

    def setUp(self):
        supp_genres = (['Исэкай', 'Школа'], ['Сёнен'])
        self.keywords = {
            title['id']: genres if genres is not None else []
            for title, genres in zip_longest(self.parent_data, supp_genres)
        }
        self.base_configuration = {
            'page': 2,
            'limit': 1,
            'rating': '1-10',
            'is_series': '',
            'year': '',
            'genre': '',
            'sequels': False,
        }

    @override_settings(DEBUG_RETURN_TEST_VARS=True)
    def _create_data(self, creation_candidates, title_ids):
        backdrops = {title.title_id: [f'https://www.example.com/{title.title_id}'] for title in creation_candidates}
        with (
            patch('services.kinopoisk_api.KinopoiskClient.get_multiple_keywords', return_value=self.keywords),
            patch('titles.models.Title.upload_poster', new=lambda self, plug: Poster(title=self)),
            patch('services.kinopoisk_api.KinopoiskClient.get_multiple_backdrops', return_value=backdrops),
        ):
            return create_movie_objs(creation_candidates, title_ids)

    def _common_tests(self, data, created_genres):
        excluded_genres = ('аниме', 'мультфильм')
        expected_ids = {obj['id'] for obj in data}
        expected_count = len(expected_ids)

        self.assertEqual(Statistic.objects.count(), expected_count)
        self.assertEqual(Poster.objects.count(), expected_count)
        self.assertEqual(Backdrop.objects.count(), expected_count)
        for title_id, supp_genres in self.keywords.items():
            if title_id not in created_genres:
                continue
            for genre in supp_genres:
                self.assertIn(genre, created_genres[title_id])

        for title in Title.objects.filter(id__in=expected_ids):
            self.assertTrue(Poster.objects.filter(title=title).exists())
            self.assertTrue(Statistic.objects.filter(title=title).exists())
            self.assertTrue(Backdrop.objects.filter(title=title).exists())
            self.assertTrue(
                all(banned_genre not in created_genres[title.kinopoisk_id] for banned_genre in excluded_genres)
            )

    @patch('services.kinopoisk_api.KinopoiskClient.get_multiple_info')
    def test_only_new_titles_are_created(self, mock_api_call):
        mock_api_call.return_value = self.parent_data
        data_to_create, title_ids = data_initialization(self.base_configuration)
        genres = self._create_data(data_to_create, title_ids)

        self._common_tests(self.parent_data, genres)

    def test_no_new_titles_created_when_they_all_are_in_db(self):
        self._create_data([], [])

        self.assertEqual(Title.objects.count(), 0)

    @patch('services.kinopoisk_api.KinopoiskClient.get_multiple_info')
    def test_links_episodes(self, mock_api_call):
        episodes = 10
        self.parent_data[0]['isSeries'] = True
        self.parent_data[0]['seasonsInfo'] = [
            {'number': 1, 'episodesCount': episodes},
            {'number': 2, 'episodesCount': episodes},
        ]
        self.parent_data[1]['isSeries'] = False
        self.parent_data[1]['seasonsInfo'] = []
        mock_api_call.return_value = self.parent_data[:2]

        data_to_create, title_ids = data_initialization(self.base_configuration)
        self._create_data(data_to_create, title_ids)

        self.assertEqual(SeasonsInfo.objects.count(), episodes * 2 + 1)


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

        join_sequels_and_prequels(data_to_join=groups)

        self._common_tests(groups)

    def test_join_sequels_and_prequels_when_there_are_no_certain_titles_in_db(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        groups = {1: [2, 3], 2: [1, 3], 3: [1, 2, 6], 4: [], 5: []}
        expected_data = {1: [2, 3], 2: [1, 3], 3: [1, 2], 4: [], 5: []}

        join_sequels_and_prequels(data_to_join=groups)

        self._common_tests(expected_data, excluded_ids=[6])

    def test_join_sequels_and_prequels_when_there_are_some_different_groups(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 9)]
        Title.objects.bulk_create(titles)
        groups = {1: [2, 3], 2: [1], 3: [1, 2], 4: [5, 9], 5: [9], 7: [8], 8: []}
        expected_data = {1: [2, 3], 2: [1, 3], 3: [1, 2], 4: [5], 5: [4], 7: [8], 8: [7]}

        join_sequels_and_prequels(data_to_join=groups)

        self._common_tests(expected_data, excluded_ids=[9])

    def test_join_sequels_and_prequels_when_they_are_empty(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 4)]
        Title.objects.bulk_create(titles)
        groups = {1: [], 2: [], 3: []}
        expected_data = {1: [], 2: [], 3: []}

        join_sequels_and_prequels(data_to_join=groups)

        self._common_tests(expected_data)

    def test_cyclic_link(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        groups = {1: [2], 2: [3], 3: []}
        expected_data = {1: [2, 3], 2: [1, 3], 3: [1, 2]}

        join_sequels_and_prequels(data_to_join=groups)

        self._common_tests(expected_data)

    def test_should_create_relations_for_existing_ids(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        groups = {1: [2, 3], 2: [1, 3], 3: [1, 2, 4]}
        expected_data = {1: [2, 3, 4], 2: [1, 3, 4], 3: [1, 2, 4], 4: [1, 2, 3]}

        join_sequels_and_prequels(data_to_join=groups)

        self._common_tests(expected_data)

    def test_should_not_create_existing_group_relations(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        Group.objects.bulk_create(
            [Group(parent_id=4, child_id=1), Group(parent_id=4, child_id=2), Group(parent_id=4, child_id=3)]
        )

        groups = {1: [2, 3], 2: [1, 3], 3: [1, 2, 4]}
        expected_data = {1: [2, 3, 4], 2: [1, 3, 4], 3: [1, 2, 4], 4: [1, 2, 3]}

        join_sequels_and_prequels(data_to_join=groups)

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

        join_studios(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=studios)

        self._common_tests(studios)

    def test_same_studio_linked_to_multiple_titles(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        studios = {1: ['Studio 1'], 2: ['Studio 1'], 3: ['Studio 1'], 4: [], 5: []}

        join_studios(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=studios)

        self._common_tests(studios)

    def test_when_some_studios_are_in_db(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        studios_before = {1: ['Studio 1'], 2: ['Studio 2']}
        studios_after = {3: ['Studio 1'], 4: ['Studio 2', 'Studio 3']}

        join_studios(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=studios_before)
        join_studios(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=studios_after)

        studios_after.update(studios_before)
        self._common_tests(studios_after)

    def test_same_genres_linked_to_one_title(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        studios = {1: ['Studio 1', 'Studio 2'], 2: ['Studio 3', 'Studio 3'], 3: [], 4: [], 5: []}

        join_studios(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=studios)

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

        return self._prepare_persons(data_from_api), {obj.kinopoisk_id: obj for obj in titles}

    def test_join_persons_creates_relations(self):
        self.title_count = 2
        self.data_count = 20
        self.step = 10

        persons, titles = self._prepare_test_data()
        join_persons(created_objs=titles, data_to_join=persons)
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
        titles = {obj.kinopoisk_id: obj for obj in titles}
        join_persons(created_objs=titles, data_to_join=persons)

        data = self._clean_data(persons)
        self.assertEqual(self.related_model.objects.count(), 5)
        self._common_tests(data, miss_links=True)

    def test_when_some_persons_are_in_db(self):
        self.title_count = 5
        self.data_count = 50
        self.step = 10

        persons, titles = self._prepare_test_data()

        persons_before = dict(itertools.islice(persons.items(), 2))
        join_persons(created_objs=titles, data_to_join=persons_before)
        data = self._clean_data(persons_before)
        self._common_tests(data)

        join_persons(created_objs=titles, data_to_join=persons)
        data = self._clean_data(persons)
        self._common_tests(data)

    def test_when_incoming_data_is_enormous(self):
        self.title_count = 250
        self.data_count = 10_000
        self.step = 40

        persons, titles = self._prepare_test_data()

        with patch('titles.models.Person.objects.filter', wraps=Person.objects.filter) as mock_filter:
            join_persons(created_objs=titles, data_to_join=persons)
            self.assertEqual(mock_filter.call_count, 2)

        data = self._clean_data(persons)
        self._common_tests(data)


class JoinGenresTestCase(TestJoinMixin, TestCase):
    def setUp(self):
        self.related_model = Collection.titles.through
        self.model = Collection
        self.related_field = 'collection__name'

    def test_join_genres_creates_relations(self):
        title_count = 5
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, title_count + 1)]
        Title.objects.bulk_create(titles)
        genres = {1: ['Жанр Жанр 1', 'Жанр 2'], 2: ['Жанр 3'], 3: ['Жанр 4'], 4: ['Жанр 5', 'Жанр 6'], 5: ['Жанр 7']}

        join_genres(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=genres)
        self.assertTrue(Collection.objects.filter(name='Жанр Жанр 1').exists())

    def test_same_genres_linked_to_multiple_titles(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        genres = {1: ['Жанр 1'], 2: ['Жанр 1'], 3: ['Жанр 1'], 4: [], 5: []}

        join_genres(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=genres)

        self._common_tests(genres)

    def test_when_some_genres_are_in_db(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        genres_before = {1: ['Жанр 1'], 2: ['Жанр 2']}
        genres_after = {3: ['Жанр 1'], 4: ['Жанр 2', 'Жанр 3']}

        join_genres(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=genres_before)
        join_genres(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=genres_after)

        genres_after.update(genres_before)
        self._common_tests(genres_after)

    def test_same_genres_linked_to_one_title(self):
        titles = [Title(id=i, kinopoisk_id=i, name=f'Title {i}') for i in range(1, 6)]
        Title.objects.bulk_create(titles)
        genres = {1: ['Жанр 1'], 2: ['Жанр 2'], 3: ['Жанр 3', 'Жанр 3'], 4: [], 5: []}

        join_genres(created_objs={obj.kinopoisk_id: obj for obj in titles}, data_to_join=genres)

        self.assertEqual(self.related_model.objects.count(), 3)
        self._common_tests(genres, miss_links=True)
