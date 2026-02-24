import json
from datetime import date
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from dateutil.relativedelta import relativedelta
from django.shortcuts import reverse
from django.test import TestCase
from django.utils.timezone import now

from comments.models import Comment
from common.utils.enums import ChartType
from lists.models import Collection
from titles.forms import TitleForm
from titles.models import (Person, RatingHistory, SeasonsInfo, Statistic,
                           Studio, Title, TitleImportLog)
from users.models import User
from video_player.models import VideoResource, VoiceOver

# Create your tests here.


class BulkTitleGeneratorViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.username = 'test1'
        cls.super_username = 'super_test'
        cls.password = '12345'
        super_email = 'super_test'
        data = {'page': 2, 'limit': 1, 'rating': '1-10', 'is_series': '', 'year': '', 'genre': '', 'sequels': False}
        TitleImportLog.objects.create(**data)
        User.objects.create_user(username=cls.username, password=cls.password)
        User.objects.create_superuser(username=cls.super_username, password=cls.password, email=super_email)

    def setUp(self):
        self.path = reverse('titles:title_generator')

    def test_anonymous_visit(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, reverse('admin:login') + '?next=' + self.path)

    def test_user_visit(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, reverse('admin:login') + '?next=' + self.path)

    def test_view_get(self):
        self.client.login(username=self.super_username, password=self.password)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['page_title'], 'Новые тайтлы | MYANIMESITE')
        self.assertTemplateUsed(response, 'titles/title_generator.html')
        self.assertEqual(
            list(response.context['history']), list(TitleImportLog.objects.all().order_by('-created_at'))
        )
        self.assertIsInstance(response.context['form'], TitleForm)

    @patch('titles.views.create_from_filters')
    def test_view_post_success(self, mock_create_from_filters):
        self.client.login(username=self.super_username, password=self.password)
        data = {'page': 1, 'limit': 1, 'rating': '1-10', 'is_series': '', 'year': '', 'genre': '', 'sequels': False}
        response = self.client.post(self.path, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(TitleImportLog.objects.filter(page=1, limit=1).exists())

    @patch('titles.views.create_from_filters')
    def test_view_post_invalid(self, mock_create_from_filters):
        self.client.login(username=self.super_username, password=self.password)
        data = {'page': 1, 'limit': 1, 'is_series': False, 'genre': '', 'sequels': False, 'rating': 15, 'year': ''}
        response = self.client.post(self.path, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(TitleImportLog.objects.filter(page=1, limit=1).exists())
        self.assertContains(response, 'error')


class IndexViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = now()
        titles = (Title(name=f'Title {i}', type=Title.MOVIE, premiere=date(1999, 1, 1)) for i in range(20))
        Title.objects.bulk_create(titles)
        new_titles = Title.objects.order_by('id')
        stats = []
        views = 100
        viewed_titles = new_titles[:10]
        for title in viewed_titles:
            stats.append(Statistic(views=views, title=title))
            views += 100
        Statistic.objects.bulk_create(stats)

        day = 1
        newest_titles = new_titles[10:15]
        for title in newest_titles:
            title.premiere = date(2000, 1, day)
            day += 1
        Title.objects.bulk_update(newest_titles, fields=['premiere'])

        upcoming_titles = new_titles[15:]
        for title in upcoming_titles:
            title.premiere = cls.today + relativedelta(years=1)
        Title.objects.bulk_update(upcoming_titles, fields=['premiere'])

    def test_view_get(self):
        path = reverse('index')

        base_q = Title.objects.with_genres()
        today = date.today()
        selections = {
            'releases': base_q.filter(premiere__lte=today).order_by('-premiere')[:20],
            'upcoming_titles': base_q.filter(premiere__gt=today).order_by('-premiere')[:20],
        }

        response = self.client.get(path)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['page_title'], 'MYANIMESITE | Онлайн кинотеатр')
        self.assertTemplateUsed(response, 'titles/index.html')
        self.assertEqual(list(response.context['upcoming_titles']), list(selections['upcoming_titles']))
        self.assertEqual(list(response.context['releases']), list(selections['releases']))


class TitleDetailViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = '12345'
        cls.username = 'test999'
        cls.user = User.objects.create_user(username=cls.username, password=cls.password)

        Title.objects.bulk_create((Title(name=f'Title {i}', type=Title.SERIES) for i in range(10)))
        cls.title = Title.objects.create(name='Title 999', type=Title.MOVIE)

        titles = Title.objects.exclude(id=cls.title.id)

        def __associate_data():
            cls.group = titles[:3]
            cls.related = titles[3:8]

            persons = list(Person.objects.filter(profession=Person.ACTOR)[:3]) + list(
                Person.objects.filter(profession=Person.DIRECTOR)[:1]
            )
            studios = Studio.objects.all()[:3]
            genres = Collection.objects.all()[:3]

            title_person = Title.persons.through
            title_studio = Title.studios.through
            title_collection = Collection.titles.through

            person_rels = (title_person(title=cls.title, person=person) for person in persons)
            studio_rels = (title_studio(title=cls.title, studio=studio) for studio in studios)
            collection_rels = (title_collection(title=cls.title, collection=collection) for collection in genres)
            title_person.objects.bulk_create(person_rels)
            title_studio.objects.bulk_create(studio_rels)
            title_collection.objects.bulk_create(collection_rels)

            Statistic.objects.create(title=cls.title, rating=8)

        actors = (Person(name=f'Actor {i}', profession=Person.ACTOR, kinopoisk_id=i) for i in range(1, 6))
        directors = (Person(name=f'Director {i}', profession=Person.DIRECTOR, kinopoisk_id=i) for i in range(6, 8))
        Person.objects.bulk_create(actors)
        Person.objects.bulk_create(directors)

        studios = (Studio(name=f'Studio {i}') for i in range(5))
        Studio.objects.bulk_create(studios)

        genres = (Collection(name=f'Genre {i}', type=Collection.GENRE, slug=f'genre_{i}') for i in range(5))
        Collection.objects.bulk_create(genres)

        voiceovers = (VoiceOver(name=f'VoiceOver {i}') for i in range(5))
        VoiceOver.objects.bulk_create(voiceovers)

        season_infos = (SeasonsInfo(title=cls.title), SeasonsInfo(title=titles.first()))
        SeasonsInfo.objects.bulk_create(season_infos)

        content_unit = SeasonsInfo.objects.get(title=cls.title)
        resources = (
            VideoResource(iframe=f'https://test/{voiceover.name}', content_unit=content_unit, voiceover=voiceover)
            for voiceover in VoiceOver.objects.all()[:2]
        )
        VideoResource.objects.bulk_create(resources)

        __associate_data()
        cls.title = (
            Title.objects.with_filmmakers().with_genres().get(id=cls.title.id)
        )

    def setUp(self):
        types = {Title.SERIES: 'series', Title.MOVIE: 'movie'}
        self.params = lambda title: {'type': types[title.type], 'title_id': title.id}
        self.path = lambda params: reverse('titles:title_page', kwargs=params)

    def _common_tests(self, response, title):
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'titles/watch.html')
        self.assertEqual(response.context['page_title'], f'{title.name} | MYANIMESITE')

    @patch('titles.views.Title.objects.groupify')
    @patch('titles.views.Title.objects.similar_by_genres')
    def test_view_get(self, mock_similar, mock_groupify):
        RatingHistory.objects.create(user=self.user, title=self.title, rating=8)

        self.client.login(username=self.username, password=self.password)

        mock_similar.return_value = self.related
        mock_groupify.return_value = self.group

        path = self.path(self.params(self.title))
        response = self.client.get(path)

        title = response.context['title']
        self._common_tests(response, self.title)
        self.assertEqual(list(response.context['related']), list(self.related))
        self.assertEqual(list(response.context['group']), list(self.group))
        self.assertEqual(title.statistic.star_fill, self.title.statistic.star_fill)
        self.assertEqual(title.external_urls, self.title.external_urls)
        self.assertTrue(response.context['is_rated'])

        self.assertEqual(list(title.actors), list(self.title.actors))
        self.assertEqual(list(title.directors), list(self.title.directors))
        self.assertEqual(list(title.genres), list(self.title.genres))
        self.assertEqual(list(title.studios.all()), list(self.title.studios.all()))
        self.assertEqual(list(title.voiceovers), list(self.title.voiceovers))

    @patch('titles.views.Title.objects.groupify', return_value=[])
    @patch('titles.views.Title.objects.similar_by_genres', return_value=[])
    def test_view_get_when_title_has_minimal_content(self, mock_similar, mock_groupify):
        empty_title = Title.objects.exclude(id=self.title.id).first()

        path = self.path(self.params(empty_title))
        response = self.client.get(path)

        title = response.context['title']
        self._common_tests(response, empty_title)
        self.assertEqual(list(response.context['related']), [])
        self.assertEqual(list(response.context['group']), [])
        self.assertEqual(title.external_urls, self.title.external_urls)
        self.assertFalse(response.context['is_rated'])

        self.assertEqual(list(title.actors), [])
        self.assertEqual(list(title.directors), [])
        self.assertEqual(list(title.genres), [])
        self.assertEqual(list(title.studios.all()), [])
        self.assertEqual(list(title.voiceovers), [])

    @patch('titles.views.Title.objects.groupify', return_value=[])
    @patch('titles.views.Title.objects.similar_by_genres', return_value=[])
    def test_view_get_when_rating_history_does_not_exist(self, mock_similar, mock_groupify):
        path = self.path(self.params(self.title))
        response = self.client.get(path)

        self._common_tests(response, self.title)
        self.assertFalse(response.context['is_rated'])

    def test_when_returns_404(self):
        test_ids = [109999, 'test', -1, 0, 108.8, '']
        for bad_id in test_ids:
            with self.subTest(title_id=bad_id):
                path = f'/movie/{bad_id}/'
                response = self.client.get(path)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_title_page_with_invalid_or_mismatched_type(self):
        test_kwargs = {'type': 'test', 'title_id': self.title.id}
        response = self.client.get(reverse('titles:title_page', kwargs=test_kwargs))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        test_kwargs = {'type': 'series', 'title_id': self.title.id}
        response = self.client.get(reverse('titles:title_page', kwargs=test_kwargs))
        self.assertRedirects(response, reverse('titles:title_page', kwargs=self.params(self.title)))


class SearchTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        genres = (Collection(name=f'Genre {i}', id=i, slug=f'genre_{i}') for i in range(1, 6))
        Collection.objects.bulk_create(genres)

    def setUp(self):
        self.path = reverse('titles:search') + '?search='

    @patch('titles.views.TitleDocument.search')
    def test_search_ajax_with_success(self, mock_media_document):
        mock_query = mock_media_document.return_value.query
        mock_to_queryset = mock_query.return_value.to_queryset
        mock_to_queryset.return_value = MagicMock()

        response = self.client.get(self.path + 'test')
        response_data = json.loads(response.content.decode())

        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertTrue(response_data['html'])
        self.assertTemplateUsed(response, 'titles/modules/_search.html')

    @patch('titles.views.TitleDocument.search')
    def test_search_ajax_with_empty_search_field(self, mock_media_document):
        response = self.client.get(self.path + '')
        response_data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response_data['html'])
        self.assertTemplateUsed(response, 'titles/modules/_search.html')
        mock_media_document.assert_not_called()

    @patch('titles.views.TitleDocument.search')
    def test_search_ajax_with_incorrect_url(self, mock_media_document):
        mock_query = mock_media_document.return_value.query
        mock_query.return_value.to_queryset.return_value = []

        response = self.client.get(reverse('titles:search') + '?test=евангелион')
        response_data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response_data['html'])
        self.assertTemplateUsed(response, 'titles/modules/_search.html')


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
        self.path = lambda chart: reverse('titles:chart', args=(chart,))

    def _common_tests(self, chart, response):
        context = response.context

        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertTemplateUsed(response, 'titles/modules/_chart.html')
        self.assertEqual(context['chart'], chart)
        self.assertEqual(context['charts'], {chart.name: chart.value for chart in ChartType})
        self.assertTrue(context['titles'])

    @patch('django.db.models.query.QuerySet.order_by')
    def test_when_chart_is_popular(self, mock_order_by):
        response = self.client.get(self.path(ChartType.POPULAR.value))
        self._common_tests(ChartType.POPULAR, response)
        mock_order_by.called_once_with('-statistic__views')

    @patch('django.db.models.query.QuerySet.order_by')
    def test_when_chart_is_rated(self, mock_order_by):
        response = self.client.get(self.path(ChartType.RATED.value))
        self._common_tests(ChartType.RATED, response)
        mock_order_by.called_once_with('-statistic__kp_rating')

    @patch('django.db.models.query.QuerySet.order_by')
    def test_when_chart_is_discussed(self, mock_order_by):
        response = self.client.get(self.path(ChartType.DISCUSSED.value))
        self._common_tests(ChartType.DISCUSSED, response)
        mock_order_by.called_once_with('-comment_count')

    def test_if_url_is_incorrect(self):
        response = self.client.get(self.path('test'))
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_code)


class SetRatingTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.username = 'test999'
        cls.password = '12345'
        cls.title = Title.objects.create(name='Title 1', id=1, type=Title.MOVIE)
        cls.user = User.objects.create_user(username=cls.username, password=cls.password, id=999)

    def setUp(self):
        self.path = lambda rating, title_id=self.title.id: reverse('titles:set_rating',
                                                                   kwargs={'rating': rating, 'title_id': title_id})

    def _common_tests(self, expected_rating, expected_votes, title_id, response, user_rating=None):
        statistic = Statistic.objects.get(title_id=title_id)

        self.assertEqual(statistic.rating, expected_rating)
        self.assertEqual(statistic.votes, expected_votes)
        self.assertEqual(
            RatingHistory.objects.get(title_id=title_id, user=self.user).rating,
            expected_rating if user_rating is None else user_rating,
        )
        self.assertEqual(
            json.loads(response.content.decode()), {'rating': f'{expected_rating:.2f}', 'votes': expected_votes}
        )

    def test_set_rating_success(self):
        Statistic.objects.create(title_id=1)

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path(10))

        self.assertEqual(HTTPStatus.OK, response.status_code)
        self._common_tests(10, 1, self.title.id, response)

    def test_set_rating_with_existing_rating(self):
        history_ratings = [7, 7, 8, 8]
        votes = len(history_ratings)

        users = [User(username=f'test{i}', password=self.password) for i in range(1, votes + 1)]
        history = (
            RatingHistory(title=self.title, user=user, rating=rating) for rating, user in zip(history_ratings, users)
        )

        User.objects.bulk_create(users)
        RatingHistory.objects.bulk_create(history)
        Statistic.objects.create(title=self.title, rating=sum(history_ratings) / votes, votes=votes)

        expected_votes = votes + 1
        expected_rating = sum([10] + history_ratings) / expected_votes

        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path(10))
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self._common_tests(expected_rating, expected_votes, self.title.id, response, 10)

    def test_set_rating_with_invalid_rating_title_id(self):
        self.client.login(username=self.username, password=self.password)

        bad_request_cases = [
            {'rating': 15, 'title_id': 1},
            {'rating': 0, 'title_id': 1},
        ]

        for case in bad_request_cases:
            with self.subTest(case=case):
                response = self.client.post(self.path(case['rating'], case['title_id']))
                self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_code)
                self.assertEqual(json.loads(response.content.decode()), {})

        response = self.client.post(self.path(8, 666))
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_code)
        self.assertEqual(json.loads(response.content.decode()), {})

    def test_set_rating_when_user_changes_existing_record(self):
        history_ratings = [7, 8, 8]
        votes = len(history_ratings) + 1

        users = [User(username=f'test{i}', password=self.password) for i in range(1, votes)]
        history = [
            RatingHistory(title=self.title, user=user, rating=rating) for rating, user in zip(history_ratings, users)
        ]
        history.append(RatingHistory(title=self.title, user=User.objects.get(username=self.username), rating=7))
        history_ratings.append(7)

        User.objects.bulk_create(users)
        RatingHistory.objects.bulk_create(history)

        Statistic.objects.create(title=self.title, rating=sum(history_ratings) / votes, votes=votes)

        history_ratings[0] = 10
        expected_rating = sum(history_ratings) / votes

        self.client.login(username=self.username, password=self.password)

        response = self.client.post(self.path(10))
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertEqual(len(RatingHistory.objects.all()), len(history_ratings))
        self._common_tests(expected_rating, votes, self.title.id, response, 10)

    def test_set_rating_redirects_unauthorized_user(self):
        response = self.client.post(self.path(10), {})
        self.assertEqual(HTTPStatus.UNAUTHORIZED, response.status_code)
