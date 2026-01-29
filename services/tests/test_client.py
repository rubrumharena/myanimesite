import unittest
import urllib
from itertools import chain
from unittest.mock import patch
from urllib.parse import urlparse

from common.utils.ui import get_partial_fill
from services.kinopoisk_api import KinopoiskClient


class BaseKinopoiskTestCase(unittest.TestCase):

    def setUp(self):
        self.success_output = {'docs': {'test': 1}}

    @patch('services.kinopoisk_api.KinopoiskClient._load_json', return_value={'docs': {'test': 1}})
    def test_info_returns_data_when_title_id_is_valid(self, mock_load_json):
        title_id = 1

        title = KinopoiskClient(title_id=title_id)
        result = title.info

        self.assertEqual(self.success_output, result)
        mock_load_json.assert_called_once_with(f'{title.BASE_URL}movie/{title_id}')

    def test_info_when_title_id_is_invalid(self):
        test_ids = [1.1, 'test', '']

        for case in test_ids:
            with self.subTest(id=case):
                title = KinopoiskClient(title_id=case)
                self.assertRaises(ValueError, lambda: title.info)

    @patch('services.kinopoisk_api.KinopoiskClient._load_json', return_value={'docs': {'test': 1}})
    def test_multiple_info_generates_expected_requests(self, mock_load_json):
        client = KinopoiskClient()
        base_url = client.BASE_URL + 'movie?' + urllib.parse.urlencode(client.DEFAULT_PARAMS, doseq=True) + '&'

        inputs = [
            {'page': 1, 'limit': 1, 'rating': '1-10', 'genre': 'Драма'},
            {'page': 2, 'limit': 30, 'rating': '10', 'is_series': True, 'year': '2015-2020'},
            {'page': 1, 'title_ids': [123, 234, 345]}]
        url_query_names = {'page': 'page', 'limit': 'limit', 'rating': 'rating.kp', 'genre': 'genres.name',
                            'year': 'year', 'is_series': 'isSeries', 'title_ids': 'id'}

        urls = []
        for test_input in inputs:
            if len(test_input.get('title_ids', [])) > 1:
                test_input['limit'] = len(test_input['title_ids'])
            params = {url_query_names[param]: str(value).lower() if param != 'title_ids' else value
                                                           for param, value in test_input.items()}
            urls.append(base_url + urllib.parse.urlencode(params, doseq=True))

        client = KinopoiskClient()
        for i, case in enumerate(inputs):
            with (self.subTest(params=case)):
                titles = client.get_multiple_info(**case)
                self.assertEqual(self.success_output['docs'], titles)
                expected_url = urls[i].split('?')
                actual_url = mock_load_json.call_args.args[0].split('?')
                self.assertEqual(expected_url[0], actual_url[0])
                self.assertEqual(sorted(expected_url[1].split('&')), sorted(actual_url[1].split('&')))


    @patch('services.kinopoisk_api.requests.get', return_value={})
    def test_multiple_info_with_invalid_parameters(self, mock_request_get):
        test_params = [{'page': 1, 'limit': 1, 'genre': 'test'},
                       {'page': 2, 'limit': 251},
                       {'title_ids': [123, 234, 'test']}]

        client = KinopoiskClient()
        for i, case in enumerate(test_params):
            with self.subTest(params=case):
                titles = client.get_multiple_info(**case)
                self.assertEqual(titles, [])


class KinopoiskKeywordsTestCase(unittest.TestCase):

    def setUp(self):
        self.success_output = {'docs': {'test': 1}}

    @patch('services.kinopoisk_api.KinopoiskClient._load_json', return_value={'docs': {'test': 1}})
    def test_load_keywords_builds_correct_url_and_returns_data(self, mock_load_json):
        client = KinopoiskClient()
        base_url = client.BASE_URL + 'keyword?' + urllib.parse.urlencode(
            {'page': 1, 'limit': 50, 'selectFields': ['title', 'movies'], 'id': client.KEYWORD_GENRES}, doseq=True) + '&'

        test_cases = [{'movies.id': 1224030}, {'movies.id': [123, 234, 345]}]

        urls = [base_url + urllib.parse.urlencode(case, doseq=True) for case in test_cases]

        for i, case in enumerate(test_cases):
            with (self.subTest(params=case)):
                title_ids = case['movies.id']
                client = KinopoiskClient(title_id=title_ids if not isinstance(title_ids, list) else None)
                self.assertEqual(self.success_output['docs'], client._load_keywords(title_ids=title_ids if isinstance(title_ids, list) else None))

                expected_url = urls[i].split('?')
                actual_url = mock_load_json.call_args.args[0].split('?')
                self.assertEqual(expected_url[0], actual_url[0])
                self.assertEqual(sorted(expected_url[1].split('&')), sorted(actual_url[1].split('&')))

    def test_load_keywords_when_titles_are_empty_list(self):
        client = KinopoiskClient()
        self.assertEqual(client._load_keywords([]), [])

    @patch('services.kinopoisk_api.KinopoiskClient._load_keywords')
    def test_get_multiple_keywords(self, mock_load_keywords):
        mock_load_keywords.return_value = [
            {'title': 'Исэкай', 'movies': [{'id': '123'}, {'id': '321'}, {'id': '234'}]},
            {'title': 'Сёнэн', 'movies': [{'id': 234}, {'id': 123}, {'id': 321}]},
            {'title': 'Этти', 'movies': [{'id': 666}]},
            {'title': 'Эротика', 'movies': [{'id': 666}]}
        ]
        result = {123: ['Исэкай', 'Сёнэн'],  321: ['Исэкай', 'Сёнэн'], 432: [], 666: ['Этти']}
        client = KinopoiskClient()
        self.assertEqual(client.get_multiple_keywords([123, 432, 321, 666]), result)

    def test_get_multiple_keywords_if_title_ids_invalid(self):
        client = KinopoiskClient()
        self.assertEqual(client.get_multiple_keywords({123: 'dd'}), {})


class KinopoiskImagesTestCase(unittest.TestCase):

    @staticmethod
    def _generate_test_data(titles_count, backdrops_per_title):
        docs = []
        for title_id in range(1, titles_count + 1):
            for backdrop_id in range(1, backdrops_per_title + 1):
                docs.append({'url': f'https://www.example.com/{title_id}_{backdrop_id}', 'movieId': title_id})
        return docs

    def _common_tests(self, titles_count):
        client = KinopoiskClient()
        backdrops = client.get_multiple_backdrops(list(range(1, titles_count + 1)))

        self.assertEqual(titles_count, len(backdrops))
        self.assertEqual(titles_count * 3, len(list(chain.from_iterable(backdrops.values()))))

    @patch('services.kinopoisk_api.KinopoiskClient._load_images')
    def test_get_multiple_backdrops_single_page_fetch(self, mock_load_images):
        titles_count = 10
        backdrops_per_title = 4
        docs = self._generate_test_data(titles_count, backdrops_per_title)
        data = {'docs': docs, 'total': titles_count * backdrops_per_title}
        mock_load_images.return_value = data

        self._common_tests(titles_count)
        self.assertEqual(1, mock_load_images.call_count)

    @patch('services.kinopoisk_api.KinopoiskClient._load_images')
    def test_get_multiple_backdrops_returns_empty_when_no_backdrops(self, mock_load_images):
        titles_count = 1
        backdrops_per_title = 0

        docs = self._generate_test_data(titles_count, backdrops_per_title)
        data = {'docs': docs, 'total': titles_count * backdrops_per_title}
        mock_load_images.return_value = data

        client = KinopoiskClient()
        backdrops = client.get_multiple_backdrops([1])

        self.assertEqual({}, backdrops)
        self.assertEqual(1, mock_load_images.call_count)

    @patch('services.kinopoisk_api.KinopoiskClient._load_images')
    def test_get_multiple_backdrops_paginates_across_multiple_pages(self, mock_load_images):
        titles_count = 3
        backdrops_per_title = 250
        docs = self._generate_test_data(titles_count, backdrops_per_title)

        json_output = [{'docs': docs[i:i + backdrops_per_title], 'total': titles_count * backdrops_per_title} for i in range(0, titles_count * backdrops_per_title + 1, backdrops_per_title)]

        mock_load_images.side_effect = json_output
        self._common_tests(titles_count)
        self.assertEqual(3, mock_load_images.call_count)

    def test_get_multiple_backdrops_returns_empty_when_no_title_ids(self):
        client = KinopoiskClient()
        backdrops = client.get_multiple_backdrops([])
        self.assertEqual({}, backdrops)

    @patch('services.kinopoisk_api.KinopoiskClient._load_images')
    def test_get_multiple_backdrops_when_only_single_backdrop_exists(self, mock_load_images):
        titles_count = 1
        backdrops_per_title = 1
        docs = self._generate_test_data(titles_count, backdrops_per_title)
        data = {'docs': docs, 'total': backdrops_per_title}
        mock_load_images.return_value = data
        client = KinopoiskClient()
        backdrops = client.get_multiple_backdrops([1])

        self.assertEqual(titles_count, mock_load_images.call_count)
        self.assertEqual(backdrops_per_title, len(backdrops))
        self.assertEqual(backdrops_per_title, len(list(chain.from_iterable(backdrops.values()))))