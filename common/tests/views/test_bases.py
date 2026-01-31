import itertools
import json
from datetime import date
from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock, patch
from urllib.parse import parse_qs, urlparse

from django.http import Http404, QueryDict
from django.shortcuts import reverse
from django.test import RequestFactory, TestCase
from django.views.generic import ListView

from common.utils.enums import ListQueryParam, ListQueryValue, ListSortOption
from common.utils.testing_components import create_image
from common.views.bases import BaseListView, BaseSettingsView
from lists.models import Collection
from titles.models import Statistic, Title
from users.models import User


class ResolvedPathParamsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Collection.objects.create(name='Mov Col', slug='top250', type=Collection.MOVIE_COLLECTION)
        Collection.objects.create(name='Ser Col', slug='popular', type=Collection.SERIES_COLLECTION)

    def setUp(self):
        self.fake_instance = MagicMock()
        self.fake_instance.kwargs = {'path_params': 'genre--action/year--2020'}
        self.base_result = {
            'genre': {'slug': 'action', 'url': 'year--2020'},
            'year': {'slug': '2020', 'url': 'genre--action'},
            'collection': {'slug': '', 'url': ''},
        }

    def _common_tests(self, actual, expected):
        for data in expected:
            with self.subTest(data=data):
                self.assertEqual(actual[data]['slug'], expected[data]['slug'])
                self.assertEqual(actual[data]['url'], expected[data]['url'])

    def test_parse_params__only_filters(self):
        actual_result = BaseListView.resolved_path_params.__get__(self.fake_instance, BaseListView)
        self._common_tests(actual_result, self.base_result)

    def test_parse_params__collection_and_filters(self):
        collection = Collection.objects.get(type=Collection.MOVIE_COLLECTION)
        self.fake_instance.kwargs['path_params'] = collection.slug + '/genre--action/year--2020'
        self.base_result['collection']['slug'] = collection.slug
        self.base_result['year']['url'] = f'{collection.slug}/{self.base_result["year"]["url"]}'
        self.base_result['genre']['url'] = f'{collection.slug}/{self.base_result["genre"]["url"]}'

        actual_result = BaseListView.resolved_path_params.__get__(self.fake_instance, BaseListView)
        self._common_tests(actual_result, self.base_result)

    def test_parse_params__only_collection(self):
        collection = Collection.objects.get(type=Collection.SERIES_COLLECTION)
        self.fake_instance.kwargs['path_params'] = collection.slug
        self.base_result['collection']['slug'] = collection.slug
        self.base_result['year']['url'] = collection.slug
        self.base_result['genre']['url'] = collection.slug
        self.base_result['year']['slug'] = ''
        self.base_result['genre']['slug'] = ''

        actual_result = BaseListView.resolved_path_params.__get__(self.fake_instance, BaseListView)
        self._common_tests(actual_result, self.base_result)

    def test_parse_params__no_path_params(self):
        self.fake_instance.kwargs['path_params'] = None
        self.base_result = {
            'genre': {'slug': '', 'url': ''},
            'year': {'slug': '', 'url': ''},
            'collection': {'slug': '', 'url': ''},
        }
        actual_result = BaseListView.resolved_path_params.__get__(self.fake_instance, BaseListView)
        self._common_tests(actual_result, self.base_result)

        self.fake_instance.kwargs['path_params'] = ''
        actual_result = BaseListView.resolved_path_params.__get__(self.fake_instance, BaseListView)
        self._common_tests(actual_result, self.base_result)

    def test_parse_params__invalid_path_params_raise_404(self):
        test_cases = [
            'test/year--2022/',
            'test--action',
            'genre-action',
            'Top250',
            'year--',
            'genre--action/top250',
            '2022--year',
            'year--2021/year--2022/',
        ]

        for case in test_cases:
            self.fake_instance.kwargs['path_params'] = case
            with self.subTest(data=case):
                with self.assertRaises(Http404):
                    BaseListView.resolved_path_params.__get__(self.fake_instance, BaseListView)

    def test_parse_params__when_folder_url_contains_collection(self):
        collection = Collection.objects.get(type=Collection.SERIES_COLLECTION)
        self.fake_instance.kwargs['path_params'] = collection.slug
        self.fake_instance.kwargs['folder_id'] = 1

        with self.assertRaises(Http404):
            BaseListView.resolved_path_params.__get__(self.fake_instance, BaseListView)


class FilterSwitchUrlsTestCase(TestCase):
    def setUp(self):
        self.fake_instance = MagicMock()
        self.fake_instance.request.path = 'lists/'

    def _common_tests(self, actual, expected):
        for param, values in expected.items():
            with self.subTest(param=param):
                query_params = parse_qs(urlparse(actual[param]).query).values()
                self.assertEqual(sorted(list(itertools.chain.from_iterable(query_params))), sorted(values))
            self.assertTrue(actual[param].startswith('lists/'))

    def test_filter_switch_urls__if_movies_active(self):
        self.fake_instance.request.GET = QueryDict('f=' + ListQueryValue.MOVIES.value)
        actual_result = BaseListView.filter_switch_urls.__get__(self.fake_instance, BaseListView)
        expected_data = {
            'movies': [],
            'series': ['series'],
            'released': ['released', 'movies'],
            'rated': ['rated', 'movies'],
        }
        self._common_tests(actual_result, expected_data)

    def test_filter_switch_urls__if_series_active(self):
        self.fake_instance.request.GET = QueryDict('f=' + ListQueryValue.SERIES.value)
        actual_result = BaseListView.filter_switch_urls.__get__(self.fake_instance, BaseListView)
        expected_data = {
            'movies': ['movies'],
            'series': [],
            'released': ['released', 'series'],
            'rated': ['rated', 'series'],
        }
        self._common_tests(actual_result, expected_data)

    def test_filter_switch_urls__with_other_f_params(self):
        self.fake_instance.request.GET = QueryDict(
            'f=' + ListQueryValue.RELEASED.value + '&f=' + ListQueryValue.RATED.value
        )
        actual_result = BaseListView.filter_switch_urls.__get__(self.fake_instance, BaseListView)
        expected_data = {
            'movies': ['released', 'rated', 'movies'],
            'series': ['released', 'rated', 'series'],
            'released': ['rated'],
            'rated': ['released'],
        }
        self._common_tests(actual_result, expected_data)

    def test_filter_switch_urls__with_other_params(self):
        self.fake_instance.request.GET = QueryDict('f=' + ListQueryValue.RELEASED.value + '&sort=rating')
        actual_result = BaseListView.filter_switch_urls.__get__(self.fake_instance, BaseListView)
        expected_data = {
            'movies': ['released', 'rating', 'movies'],
            'series': ['released', 'rating', 'series'],
            'released': ['rating'],
            'rated': ['released', 'rated', 'rating'],
        }
        self._common_tests(actual_result, expected_data)

    def test_filter_switch_urls__with_mixed_params(self):
        self.fake_instance.request.GET = QueryDict(
            'f=' + ListQueryValue.RELEASED.value + '&sort=rating' + '&f=' + ListQueryValue.SERIES.value
        )
        actual_result = BaseListView.filter_switch_urls.__get__(self.fake_instance, BaseListView)
        expected_data = {
            'movies': ['released', 'rating', 'movies'],
            'series': ['released', 'rating'],
            'released': ['rating', 'series'],
            'rated': ['released', 'rated', 'rating', 'series'],
        }
        self._common_tests(actual_result, expected_data)

    def test_filter_switch_urls__if_series_and_movies_active_together(self):
        self.fake_instance.request.GET = QueryDict(
            'f=' + ListQueryValue.SERIES.value + '&f=' + ListQueryValue.MOVIES.value
        )
        actual_result = BaseListView.filter_switch_urls.__get__(self.fake_instance, BaseListView)
        expected_data = {
            'movies': [],
            'series': [],
            'released': ['released', 'series', 'movies'],
            'rated': ['rated', 'series', 'movies'],
        }
        self._common_tests(actual_result, expected_data)

    def test_filter_switch_urls__if_params_empty(self):
        self.fake_instance.request.GET = QueryDict('f=')
        actual_result = BaseListView.filter_switch_urls.__get__(self.fake_instance, BaseListView)
        expected_data = {'movies': ['movies'], 'series': ['series'], 'released': ['released'], 'rated': ['rated']}
        self._common_tests(actual_result, expected_data)

    def test_filter_switch_urls__if_one_param_active_twice(self):
        self.fake_instance.request.GET = QueryDict(
            'f=' + ListQueryValue.RELEASED.value + '&f=' + ListQueryValue.RELEASED.value
        )
        actual_result = BaseListView.filter_switch_urls.__get__(self.fake_instance, BaseListView)
        expected_data = {
            'movies': ['movies', 'released', 'released'],
            'series': ['series', 'released', 'released'],
            'released': [],
            'rated': ['rated', 'released', 'released'],
        }
        self._common_tests(actual_result, expected_data)

    def test_filter_switch_urls__if_no_f_params(self):
        self.fake_instance.request.GET = QueryDict('')
        actual_result = BaseListView.filter_switch_urls.__get__(self.fake_instance, BaseListView)
        expected_data = {'movies': ['movies'], 'series': ['series'], 'released': ['released'], 'rated': ['rated']}
        self._common_tests(actual_result, expected_data)


class PrepareListFilterItems(TestCase):
    def setUp(self):
        self.fake_instance = MagicMock()
        self.fake_instance.resolved_path_params = {'genre': {'slug': '', 'url': ''}, 'year': {'slug': '', 'url': ''}}
        self.fake_instance.route = reverse('lists:folder', kwargs={'folder_id': 1})
        self.items = [{'name': f'Жанр {i}', 'slug': f'slug_{i}'} for i in range(10)]

    def test_when_any_is_active_and_no_path_params(self):
        expected_result = {
            'url': reverse('lists:folder', kwargs={'folder_id': 1}),
            'is_selected': True,
            'name': 'Любой',
        }
        result = BaseListView.prepare_list_filter_items(self.fake_instance, self.items, ListQueryParam.GENRES.value)
        self.assertEqual(result[0], expected_result)

    def test_happy_path(self):
        root_url = 'year--slug_2'
        slug = 'slug_1'
        expected_result = [
            {
                'url': reverse('lists:folder', kwargs={'path_params': root_url, 'folder_id': 1}),
                'is_selected': False,
                'name': 'Любой',
            }
        ]

        self.fake_instance.resolved_path_params['genre']['slug'] = slug
        self.fake_instance.resolved_path_params['genre']['url'] = root_url
        for item in self.items:
            item_slug = item['slug']
            url = reverse(
                'lists:folder', kwargs={'path_params': root_url + '/' + f'genre--{item_slug}', 'folder_id': 1}
            )

            expected_result.append({'url': url, 'is_selected': slug == item_slug, 'name': item['name']})
        result = BaseListView.prepare_list_filter_items(self.fake_instance, self.items, ListQueryParam.GENRES.value)

        for expected, actual in zip(expected_result, result):
            self.assertEqual(expected, actual)

    def test_invalid_type(self):
        with self.assertRaises(Http404):
            BaseListView.prepare_list_filter_items(self.fake_instance, self.items, 'test')


class GenerateCollectionTitleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Collection.objects.create(name='Mov Col', slug='mov_col', type=Collection.MOVIE_COLLECTION)
        Collection.objects.create(name='Genre', slug='genre', type=Collection.GENRE)

    def setUp(self):
        self.parsed_params = {'genre': {'slug': ''}, 'year': {'slug': ''}, 'collection': {'slug': ''}}
        self.instance = BaseListView()

    def test_if_movie_collection(self):
        params = self.parsed_params
        collection = Collection.objects.get(type=Collection.MOVIE_COLLECTION)
        params['collection']['slug'] = collection.slug
        params['genre']['slug'] = 'test'
        expected_title = collection.name

        self.assertEqual(self.instance.generate_collection_title(params, []), expected_title)

    def test_if_genre(self):
        params = self.parsed_params
        collection = Collection.objects.get(type=Collection.GENRE)
        params['genre']['slug'] = collection.slug
        expected_title = collection.name + ' - аниме фильмы и сериалы'

        self.assertEqual(self.instance.generate_collection_title(params, []), expected_title)

    def test_if_genre_and_movies(self):
        params = self.parsed_params
        collection = Collection.objects.get(type=Collection.GENRE)
        params['genre']['slug'] = collection.slug
        expected_title = collection.name + ' - аниме фильмы'

        self.assertEqual(self.instance.generate_collection_title(params, [ListQueryValue.MOVIES.value]), expected_title)

    def test_if_genre_and_series(self):
        params = self.parsed_params
        collection = Collection.objects.get(type=Collection.GENRE)
        params['genre']['slug'] = collection.slug
        expected_title = collection.name + ' - аниме сериалы'

        self.assertEqual(self.instance.generate_collection_title(params, [ListQueryValue.SERIES.value]), expected_title)

    def test_if_genre_and_series_and_movies(self):
        params = self.parsed_params
        collection = Collection.objects.get(type=Collection.GENRE)
        params['genre']['slug'] = collection.slug
        expected_title = collection.name + ' - аниме фильмы и сериалы'

        self.assertEqual(
            self.instance.generate_collection_title(params, [ListQueryValue.SERIES.value, ListQueryValue.MOVIES.value]),
            expected_title,
        )

    def test_if_genre_series_and_year(self):
        params = self.parsed_params
        collection = Collection.objects.get(type=Collection.GENRE)
        params['genre']['slug'] = collection.slug
        params['year']['slug'] = '2020'
        expected_title = collection.name + ' 2020 года - аниме сериалы'

        self.assertEqual(self.instance.generate_collection_title(params, [ListQueryValue.SERIES.value]), expected_title)

    def test_if_genre_and_year(self):
        params = self.parsed_params
        collection = Collection.objects.get(type=Collection.GENRE)
        params['genre']['slug'] = collection.slug
        params['year']['slug'] = '2020'
        expected_title = collection.name + ' 2020 года - аниме фильмы и сериалы'

        self.assertEqual(self.instance.generate_collection_title(params, []), expected_title)

    def test_if_series_and_movies_and_year_range(self):
        params = self.parsed_params
        params['year']['slug'] = '2000-2009'
        expected_title = 'Аниме фильмы и сериалы 2000-х годов'

        self.assertEqual(self.instance.generate_collection_title(params, []), expected_title)


class PrepareFlagsTestCase(TestCase):
    def setUp(self):
        self.view = BaseListView()
        self.filters = {
            'movies': False,
            'series': False,
            'released': False,
            'unwatched': False,
            'rated': False,
            'blocked': False,
        }

        self.view.request = MagicMock()

    def test_when_filtered_by_movie(self):
        self.view.request.GET = QueryDict(f'f={ListQueryValue.MOVIES.value}')

        actual_result = self.view.prepare_flags([1, 2, 3])
        self.filters['movies'] = True

        self.assertEqual(actual_result, self.filters)

    def test_when_filtered_by_series(self):
        self.view.request.GET = QueryDict(f'f={ListQueryValue.SERIES.value}')

        actual_result = self.view.prepare_flags([1, 2, 3])
        self.filters['series'] = True

        self.assertEqual(actual_result, self.filters)

    def test_when_filtered_by_released_unwatched_rated(self):
        self.view.request.GET = QueryDict(
            f'f={ListQueryValue.RELEASED.value}&f={ListQueryValue.UNWATCHED.value}&f={ListQueryValue.RATED.value}'
        )

        actual_result = self.view.prepare_flags([1, 2, 3])
        self.filters['released'] = True
        self.filters['unwatched'] = True
        self.filters['rated'] = True

        self.assertEqual(actual_result, self.filters)

    def test_when_filtered_by_movies_and_series(self):
        self.view.request.GET = QueryDict(f'f={ListQueryValue.MOVIES.value}&f={ListQueryValue.SERIES.value}')

        actual_result = self.view.prepare_flags([1, 2, 3])
        self.filters['series'] = True
        self.filters['movies'] = True
        self.filters['blocked'] = True

        self.assertEqual(actual_result, self.filters)

    def test_when_no_queryset(self):
        self.view.request.GET = QueryDict()

        actual_result = self.view.prepare_flags([])
        self.filters['blocked'] = True

        self.assertEqual(actual_result, self.filters)

    def test_when_filtered_by_nothing(self):
        self.view.request.GET = QueryDict()

        actual_result = self.view.prepare_flags([1, 2, 3])

        self.assertEqual(actual_result, self.filters)


class BaseListViewTestCase(TestCase):
    class DummyView(BaseListView, ListView): ...

    @classmethod
    def setUpTestData(cls):
        today = date.today()
        titles = [
            Title(name=f'Title {i}', id=i, type=Title.MOVIE, year=2000 + i, premiere=f'{today.year + 2 - i}-01-01')
            for i in range(1, 11)
        ]
        col_titles = [Title(name=f'Title {i}', id=i, type=Title.MOVIE) for i in range(11, 16)]
        Title.objects.bulk_create(titles + col_titles)
        genres = [Collection(name=f'Genre {i}', id=i, type=Collection.GENRE, slug=f'genre_{i}') for i in range(1, 11)]
        Collection.objects.bulk_create(genres)

        for title in titles:
            title.collections.add(Collection.objects.get(id=title.id))

        collection = Collection.objects.create(name='Top 250', type=Collection.MOVIE_COLLECTION, slug='top250', id=11)
        for title in col_titles:
            title.collections.add(collection)

    def setUp(self):
        self.dummy_view = self.DummyView
        self.fake_instance = MagicMock()
        self.fake_instance.kwargs = {}
        self.fake_instance.sort_method = 'created_at'
        self.fake_instance._internal_queryset_call = False
        self.fake_instance.request.GET = QueryDict()

    def _common_path_param_tests(self, path_params, expected_data):
        self.fake_instance.kwargs = {'path_params': path_params}
        self.resolved_path_params = self.dummy_view.resolved_path_params.__get__(self.fake_instance, self.dummy_view)

        self.assertEqual(
            list(self.dummy_view.get_queryset(self.fake_instance)), list(expected_data.order_by('created_at'))
        )

    def _common_query_param_tests(self, f_params, expected_data):
        self.fake_instance.request.GET = QueryDict(f_params)

        self.assertEqual(
            list(self.dummy_view.get_queryset(self.fake_instance)), list(expected_data.order_by('created_at'))
        )

    def test_queryset__when_genre_param(self):
        self._common_path_param_tests('genre--genre_1', Title.objects.filter(collections__id=1))

    def test_queryset__when_year_param(self):
        self._common_path_param_tests('year--2005', Title.objects.filter(collections__id=5))

    def test_queryset__when_year_range_param(self):
        self._common_path_param_tests('year--2001-2005', Title.objects.filter(collections__id__in=range(1, 6)))

    def test_queryset__when_collection_param(self):
        self._common_path_param_tests('top250', Title.objects.filter(collections__type=Collection.MOVIE_COLLECTION))

    def test_queryset__when_no_path_params(self):
        self.assertEqual(list(self.dummy_view.get_queryset(self.fake_instance)), list(Title.objects.all()))

    def test_queryset__when_movie_param(self):
        self._common_query_param_tests(f'f={ListQueryValue.MOVIES.value}', Title.objects.filter(type=Title.MOVIE))

    def test_queryset__when_series_param(self):
        self._common_query_param_tests(f'f={ListQueryValue.SERIES.value}', Title.objects.filter(type=Title.SERIES))

    def test_queryset__when_series_and_movie_param(self):
        self._common_query_param_tests(
            f'f={ListQueryValue.SERIES.value}&f={ListQueryValue.MOVIES.value}', Title.objects.none()
        )

    def test_queryset__when_released_param(self):
        self._common_query_param_tests(
            f'f={ListQueryValue.RELEASED.value}', Title.objects.filter(premiere__lte=date.today())
        )

    def test_queryset__when_rated_param(self):
        self._common_query_param_tests(
            f'f={ListQueryValue.RATED.value}', Title.objects.filter(statistic__kp_rating__gte=7)
        )

    def test_queryset__when_best_param(self):
        titles = [Title(name=f'New Title {i}', id=i) for i in range(100, 131)]
        Title.objects.bulk_create(titles)
        stats = [Statistic(kp_rating=8, kp_votes=900, title=title) for title in titles]
        Statistic.objects.bulk_create(stats)
        for title in titles:
            title.collections.add(Collection.objects.get(id=1))

        self.fake_instance.request.GET = QueryDict(f'tab={ListQueryValue.BEST.value}')
        self.assertEqual(self.dummy_view.get_queryset(self.fake_instance).count(), 20)

    @patch('common.views.bases.BaseListView.prepare_flags')
    @patch('common.views.bases.BaseListView.resolved_path_params', new_callable=PropertyMock)
    @patch('common.views.bases.BaseListView.filter_switch_urls', new_callable=PropertyMock)
    @patch('common.views.bases.BaseListView.get_queryset')
    @patch('common.views.bases.BaseListView.prepare_list_filter_items')
    def test_context_data(
        self,
        mock_prepare_list_filter_items,
        mock_get_queryset,
        mock_filter_switch_urls,
        mock_resolved_path_params,
        mock_prepare_flags,
    ):
        return_value = {'test': True}
        mock_get_queryset.return_value = Title.objects.filter(collections__type=Collection.GENRE)
        mock_filter_switch_urls.return_value = return_value
        mock_resolved_path_params.return_value = return_value
        mock_prepare_list_filter_items.return_value = return_value
        mock_prepare_flags.return_value = return_value

        request = RequestFactory()
        self.dummy_view.request = request.get('/')
        self.dummy_view.args = []
        self.dummy_view.kwargs = {}
        self.dummy_view.object_list = []
        self.dummy_view.request.GET = QueryDict()

        context = self.dummy_view().get_context_data()

        self.assertEqual(context['sort_methods'], {option.value: option.label for option in ListSortOption})
        self.assertEqual(context['params'], {param.name: param.value for param in ListQueryParam})
        self.assertEqual(context['query_values'], {f_param.name: f_param.value for f_param in ListQueryValue})
        self.assertEqual(context['genre_filters'], return_value)
        self.assertEqual(context['year_filters'], return_value)
        self.assertEqual(context['filter_urls'], return_value)
        self.assertEqual(context['path_params'], return_value)
        self.assertEqual(context['flags'], return_value)
        self.assertEqual(context['all_titles_count'], Title.objects.filter(collections__type=Collection.GENRE).count())
        self.assertEqual(context['best_titles_count'], 0)


class BaseSettingsViewTestCase(TestCase):
    class DummyView(BaseSettingsView, ListView): ...

    def setUp(self):
        self.username = 'test'
        self.password = '123456'
        self.user = User.objects.create_user(
            username=self.username, email='test@gmail.com', password=self.password, avatar=create_image('test')
        )

        self.factory = RequestFactory()
        self.form_map = {'test1': MagicMock, 'test2': MagicMock}
        self.view = self.DummyView()
        self.view.form_map = self.form_map
        self.view.template_name = 'test.html'
        self.request = self.factory.get('/test/')
        self.request.user = self.user
        self.view.setup(self.request)
        self.side_effect = [MagicMock(form='form1'), MagicMock(form='form2')]

    @patch('common.views.bases.BaseSettingsView.get_forms', return_value={})
    @patch('common.views.bases.render_to_string', return_value='test')
    def test_view_get(self, mock_render_to_string, mock_get_forms):
        response = self.view.get(self.request)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn('html', data)
        self.assertIn(data['html'], 'test')

    @patch('common.views.bases.BaseSettingsView.get_forms', return_value={})
    @patch('common.views.bases.render_to_string', return_value='test')
    @patch('common.views.bases.BaseSettingsView.build_form')
    def test_post_valid(self, mock_build_form, mock_render_to_string, mock_get_forms):
        mock_build_form.return_value = self.side_effect[0]
        self.request.POST = QueryDict('form=test1')
        response = self.view.post(self.request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(data['html'], 'test')

    @patch('common.views.bases.render_to_string', return_value='test')
    @patch('common.views.bases.BaseSettingsView.build_form')
    def test_post_invalid(self, mock_build_form, mock_render_to_string):
        form = self.side_effect[1]
        form.is_valid.return_value = False
        mock_build_form.return_value = form
        self.request.POST = QueryDict('form=test2')
        response = self.view.post(self.request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn('html', data)
        self.assertIn(data['html'], 'test')

    @patch('common.views.bases.BaseSettingsView.build_form')
    def test_post_404(self, mock_build_form):
        mock_build_form.return_value = None
        self.request.POST = QueryDict('form=test999')
        with self.assertRaises(Http404):
            self.view.post(self.request)

    @patch('common.views.bases.BaseSettingsView.build_form')
    def test_get_forms_happy_path(self, mock_build_form):
        mock_build_form.side_effect = self.side_effect
        form = MagicMock(form='form2')
        form.edited = True

        forms = self.view.get_forms(form)
        self.assertIsInstance(forms['test1'], MagicMock)
        self.assertIsInstance(forms['test2'], MagicMock)
        self.assertTrue('username', forms['test1'].edited)

    @patch('common.views.bases.BaseSettingsView.build_form')
    def test_get_forms_when_no_active_form(self, mock_build_form):
        mock_build_form.side_effect = self.side_effect

        forms = self.view.get_forms()
        self.assertIsInstance(forms['test1'], MagicMock)
        self.assertIsInstance(forms['test2'], MagicMock)
