import json
from http import HTTPStatus
from unittest.mock import patch, MagicMock

from django.shortcuts import reverse
from django.test import TestCase

from comments.models import Comment
from common.utils.enums import ChartType
from titles.models import Title, Statistic, RatingHistory, SeasonsInfo, Poster
from titles.views import get_chart_ajax
from users.models import User
from lists.models import Collection
from video_player.models import ViewingHistory


class SearchTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        genres = (Collection(name=f'Genre {i}', id=i, slug=f'genre_{i}') for i in range(1, 6))
        Collection.objects.bulk_create(genres)

    def setUp(self):
        self.path = reverse('titles:search_ajax') + '?search_field='
        self.empty_response = {'items': []}

    @patch('titles.views.TitleDocument.search')
    def test_search_ajax_with_success(self, mock_media_document):
        fake_data = {'id': 1, 'name': 'Евангелион', 'year': 1999, 'genres': list(Collection.objects.filter(id__in=[1, 2, 3]).values_list('name', flat=True)),
                        'type': Title.MOVIE, 'image': None, 'url': reverse('titles:title_page', kwargs={'type': 'movie', 'title_id':1})}

        fake_title = MagicMock()
        fake_title.name = fake_data['name']
        fake_title.year = fake_data['year']
        fake_title.poster = Poster()
        fake_title.type = fake_data['type']
        fake_title.id = 1
        fake_title.collections.filter.return_value.distinct.return_value = Collection.objects.filter(id__in=[1, 2, 3])

        mock_query = mock_media_document.return_value.query
        mock_to_queryset = mock_query.return_value.to_queryset
        mock_to_queryset.return_value = [fake_title]

        response = self.client.get(self.path + 'евангелион')
        response_data = json.loads(response.content.decode())['items'][0]

        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertEqual(fake_data, response_data)

    def test_search_ajax_with_empty_search_field(self):
        response = self.client.get(self.path + '')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(json.loads(response.content.decode()), self.empty_response)

    @patch('titles.views.TitleDocument.search')
    def test_search_ajax_with_no_results(self, mock_media_document):
        mock_query = mock_media_document.return_value.query
        mock_query.return_value.to_queryset.return_value = []
        response = self.client.get(self.path + 'евангелион')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(json.loads(response.content.decode()), self.empty_response)

    @patch('titles.views.TitleDocument.search')
    def test_search_ajax_with_incorrect_url(self, mock_media_document):
        mock_query = mock_media_document.return_value.query
        mock_query.return_value.to_queryset.return_value = []
        response = self.client.get(reverse('titles:search_ajax') + '?test=евангелион')
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(json.loads(response.content.decode()), self.empty_response)


class SetRatingTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.username = 'test999'
        cls.password = '12345'
        Title.objects.create(name='Title 1', id=1, type=Title.MOVIE)
        cls.user = User.objects.create_user(username=cls.username, password=cls.password, id=999)

    def setUp(self):
        self.path = reverse('titles:set_rating_ajax')

    def _common_tests(self, expected_rating, expected_votes, title_id, response, user_rating=None):
        statistic = Statistic.objects.get(title_id=title_id)

        self.assertEqual(statistic.rating, expected_rating)
        self.assertEqual(statistic.votes, expected_votes)
        self.assertEqual(RatingHistory.objects.get(title_id=title_id, user=self.user).rating,
                         expected_rating if user_rating is None else user_rating)
        self.assertEqual(json.loads(response.content.decode()), {'rating': f'{expected_rating:.2f}', 'votes': expected_votes})

    def test_set_rating_success(self):
        Statistic.objects.create(title_id=1)

        data = {'rating': 10, 'title_id': 1}
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, data)

        self.assertEqual(HTTPStatus.OK, response.status_code)
        self._common_tests(data['rating'], 1, data['title_id'], response)

    def test_set_rating_with_existing_rating(self):
        title_id = 1
        history_ratings = [7, 7, 8, 8]
        votes = len(history_ratings)

        users = [User(username=f'test{i}', password=self.password) for i in range(1, votes+1)]
        history = (RatingHistory(title_id=title_id, user=user, rating=rating) for rating, user in zip(history_ratings, users))

        User.objects.bulk_create(users)
        RatingHistory.objects.bulk_create(history)
        Statistic.objects.create(title_id=title_id, rating=sum(history_ratings)/votes, votes=votes)

        data = {'rating': 10, 'title_id': title_id}

        expected_votes = votes + 1
        expected_rating = sum([10] + history_ratings) / expected_votes

        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path, data)
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self._common_tests(expected_rating, expected_votes, title_id, response, user_rating=data['rating'])

    def test_set_rating_with_invalid_rating_title_id(self):
        self.client.login(username=self.username, password=self.password)

        bad_request_cases = [
            {'rating': 'test', 'title_id': 1},
            {'rating': '', 'title_id': 1},
            {'rating': 15, 'title_id': 1},
            {'rating': 0, 'title_id': 1},
            {'rating': 10, 'title_id': 'test'},
            {'rating': 10, 'title_id': ''},
        ]

        for case in bad_request_cases:
            with self.subTest(case=case):
                response = self.client.post(self.path, case)
                self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_code)
                self.assertEqual(json.loads(response.content.decode()), {})

        response = self.client.post(self.path, {'rating': 10, 'title_id': 666})
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_code)
        self.assertEqual(json.loads(response.content.decode()), {})

    def test_set_rating_when_user_changes_existing_record(self):
        title_id = 1
        history_ratings = [7, 8, 8]
        votes = len(history_ratings) + 1

        users = [User(username=f'test{i}', password=self.password) for i in range(1, votes)]
        history = [RatingHistory(title_id=title_id, user=user, rating=rating) for rating, user in zip(history_ratings, users)]
        history.append(RatingHistory(title_id=title_id, user=User.objects.get(username=self.username), rating=7))
        history_ratings.append(7)

        User.objects.bulk_create(users)
        RatingHistory.objects.bulk_create(history)

        Statistic.objects.create(title_id=title_id, rating=sum(history_ratings)/votes, votes=votes)

        data = {'rating': 1, 'title_id': title_id}

        history_ratings[0] = data['rating']
        expected_rating = sum(history_ratings) / votes

        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path, data)
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertEqual(len(RatingHistory.objects.all()), len(history_ratings))
        self._common_tests(expected_rating, votes, title_id, response, user_rating=data['rating'])

    def test_set_rating_redirects_unauthorized_user(self):
        response = self.client.post(self.path, {})
        self.assertEqual(HTTPStatus.UNAUTHORIZED, response.status_code)


class GetChartTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        titles = [Title(name=f'Title {i}', id=i, type=Title.MOVIE) for i in range(1, 11)]
        users = [User(username=f'user_{i}', id=i, password=12345) for i in range(1, 11)]
        Title.objects.bulk_create(titles)
        User.objects.bulk_create(users)

        views = 1_000
        rating = 10
        comments_count = 100
        stats, comments = [], []

        for title, user in zip(titles, users):
            comments += [Comment(title=title, text='Test', user=user) for _ in range(comments_count)]
            stats.append(Statistic(title=title, views=views, kp_rating=rating))
            views -= 100
            rating -= 1
            comments_count -= 10

        Comment.objects.bulk_create(comments)
        Statistic.objects.bulk_create(stats)

    def setUp(self):
        self.path = reverse('titles:get_chart_ajax') + '?type='
        self.data = [
            {
                'id': title.id,
                'name': title.name,
                'type': title.type,
                'year': None,
                'genres': None,
                'small_poster': None,
                'medium_poster': None,

                'views': 0,
                'rating': 0,
                'comments': 0
            } for title in Title.objects.all()
        ]

    def _common_tests(self, expected_data, response):
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content.decode())['items']

        for expected_item, actual_item in zip(expected_data, data):
            with self.subTest(case=expected_item['id']):
                for key in expected_item:
                    self.assertEqual(expected_item[key], actual_item[key])

    def test_when_chart_is_popular(self):
        response = self.client.get(self.path + ChartType.POPULAR.value)
        for title, data in zip(Title.objects.order_by('id'), self.data):
            data['views'] = title.statistic.views

        self._common_tests(self.data, response)

    def test_when_chart_is_rated(self):
        response = self.client.get(self.path + ChartType.RATED.value)
        for title, data in zip(Title.objects.order_by('id'), self.data):
            data['rating'] = f'{title.statistic.kp_rating:.2f}'

        self._common_tests(self.data, response)

    def test_when_chart_is_discussed(self):
        comments_count = 100
        response = self.client.get(self.path + ChartType.DISCUSSED.value)
        for title, data in zip(Title.objects.order_by('id'), self.data):
            data['comments'] = comments_count
            comments_count -= 10

        self._common_tests(self.data, response)

    def test_if_posters_handled(self):
        posters = (Poster(title=title, original=f'posters/{i}', small=f'posters/{i}', medium=f'posters/{i}') for i, title in enumerate(Title.objects.order_by('id')))
        Poster.objects.bulk_create(posters)

        response = self.client.get(self.path + ChartType.POPULAR.value)
        for title, data in zip(Title.objects.order_by('id'), self.data):
            data['views'] = title.statistic.views
            data['small_poster'] = title.poster.small.url
            data['medium_poster'] = title.poster.medium.url

        self._common_tests(self.data, response)

    def test_if_url_is_incorrect(self):
        response = self.client.get(self.path + 'test')
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_code)
        self.assertEqual(json.loads(response.content.decode()), {'items': []})

