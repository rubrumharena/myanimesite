import json
from unittest.mock import DEFAULT, MagicMock, patch

from django.test import TestCase

from services.kinopoisk_import import assemble_atomic, batch_posters, prepare_creation_candidates
from titles.models import Statistic, Title


class PrepareCreationCandidatesTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        with open('services/fixtures/first_batch.json', encoding='utf-8') as file:
            cls.parent_data = json.load(file)

        with open('services/fixtures/second_batch.json', encoding='utf-8') as file:
            cls.child_data = json.load(file)

    @patch('services.kinopoisk_api.KinopoiskClient.get_multiple_info')
    def test_returns_original_and_sequels_if_sequels_enabled(self, mock_api_call):
        mock_api_call.side_effect = [self.child_data]
        expected_ids = {obj['id'] for obj in self.parent_data + self.child_data}

        titles = prepare_creation_candidates(self.parent_data, is_sequels=True)

        self.assertEqual(mock_api_call.call_count, 1)
        self.assertEqual(len(titles), len(expected_ids))

    @patch('services.kinopoisk_api.KinopoiskClient.get_multiple_info')
    def test_data_initialization_returns_only_originals_if_sequels_enabled_but_empty(self, mock_api_call):
        mock_api_call.return_value = self.parent_data
        expected_ids = {obj['id'] for obj in self.parent_data}

        for title in self.parent_data:
            title['sequelsAndPrequels'] = []

        titles = prepare_creation_candidates(self.parent_data, is_sequels=True)

        self.assertEqual(mock_api_call.call_count, 1)
        self.assertEqual(len(titles), len(expected_ids))

    def test_base_data_initialization(self):
        expected_ids = {obj['id'] for obj in self.parent_data}

        titles = prepare_creation_candidates(self.parent_data)

        self.assertEqual(len(titles), len(expected_ids))

    def test_data_initialization_includes_sequels_from_initial_response_when_enabled(self):
        for title in self.child_data:
            title['sequelsAndPrequels'] = []

        united_data = self.child_data + self.parent_data
        expected_ids = {obj['id'] for obj in united_data}

        titles = prepare_creation_candidates(united_data)
        self.assertEqual(len(titles), len(expected_ids))

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

        mock_api_call.side_effect = [expected_child_value]
        titles = prepare_creation_candidates(expected_parent_value, is_sequels=True)

        self.assertEqual(mock_api_call.call_count, 1)
        self.assertEqual(len(titles), len(expected_ids))


class AssembleAtomicTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        with open('services/fixtures/first_batch.json', encoding='utf-8') as file:
            cls.parent_data = json.load(file)

        with open('services/fixtures/second_batch.json', encoding='utf-8') as file:
            cls.child_data = json.load(file)

    @patch.multiple(
        'services.kinopoisk_import',
        join_sequels_and_prequels=DEFAULT,
        join_studios=DEFAULT,
        join_persons=DEFAULT,
    )
    @patch('services.kinopoisk_import.SeasonsInfo.objects.bulk_create')
    @patch('services.kinopoisk_import.generate_episode_structure')
    def test_happy_path(self, mock_generate_episode_structure, mock_season_info_bulk, **mocks):
        data = prepare_creation_candidates(self.parent_data)
        persons = {obj.title_id: obj.persons for obj in data}
        studios = {obj.title_id: obj.production_companies for obj in data}
        groups = {obj.title_id: obj.sequels_and_prequels for obj in data}
        structure = [
            [MagicMock(title_id=obj.title_id)] if obj.seasons_info else MagicMock(title_id=obj.title_id) for obj in data
        ]
        mock_generate_episode_structure.side_effect = structure
        assemble_atomic(data)

        self.assertEqual(Title.objects.count(), len(data))
        self.assertEqual(Statistic.objects.count(), len(data))

        mocks['join_sequels_and_prequels'].assert_called_once_with(groups)
        mocks['join_studios'].assert_called_once_with(studios)
        mocks['join_persons'].assert_called_once_with(persons)
        mock_season_info_bulk.assert_called_once()

    @patch.multiple(
        'services.kinopoisk_import',
        join_sequels_and_prequels=DEFAULT,
        join_studios=DEFAULT,
        join_persons=DEFAULT,
    )
    @patch.multiple(
        'services.kinopoisk_import',
        SeasonsInfo=DEFAULT,
        Statistic=DEFAULT,
        Title=DEFAULT,
    )
    def test_no_titles(self, **mocks):
        assemble_atomic([])

        mocks['SeasonsInfo'].objects.bulk_create.assert_not_called()
        mocks['Statistic'].objects.bulk_create.assert_not_called()
        mocks['Title'].objects.bulk_create.assert_not_called()
        mocks['join_sequels_and_prequels'].assert_not_called()
        mocks['join_studios'].assert_not_called()
        mocks['join_persons'].assert_not_called()


class BatchPostersTestCase(TestCase):
    def setUp(self):
        self.data = [MagicMock(title_id=i, poster=f'poster_{i}') for i in range(95)]

    @patch('services.kinopoisk_import.load_posters.delay')
    def test_batches_correctly(self, mock_delay):
        batch_posters(self.data)

        self.assertEqual(mock_delay.call_count, 4)

        batch_sizes = [len(call.args[0]) for call in mock_delay.call_args_list]
        self.assertEqual(batch_sizes, [30, 30, 30, 5])
