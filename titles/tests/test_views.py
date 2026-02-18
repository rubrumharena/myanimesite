from datetime import date
from http import HTTPStatus
from unittest.mock import PropertyMock, patch

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Prefetch, Q
from django.shortcuts import reverse
from django.test import TestCase
from django.utils.timezone import now

from lists.models import Collection
from titles.forms import TitleForm
from titles.models import (Person, RatingHistory, SeasonsInfo, Statistic,
                           Studio, Title, TitleCreationHistory)
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
        TitleCreationHistory.objects.create(**data)
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
            list(response.context['history']), list(TitleCreationHistory.objects.all().order_by('-created_at'))
        )
        self.assertIsInstance(response.context['form'], TitleForm)

    @patch('titles.views.create_movie_objs')
    @patch('titles.views.data_initialization', return_value=([], []))
    def test_view_post_success(self, mock_data_initialization, mock_create_movie_objs):
        self.client.login(username=self.super_username, password=self.password)
        data = {'page': 1, 'limit': 1, 'rating': '1-10', 'is_series': '', 'year': '', 'genre': '', 'sequels': False}
        response = self.client.post(self.path, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(TitleCreationHistory.objects.filter(page=1, limit=1).exists())

    @patch('titles.views.create_movie_objs')
    @patch('titles.views.data_initialization', return_value=[])
    def test_view_post_invalid(self, mock_data_initialization, mock_create_movie_objs):
        self.client.login(username=self.super_username, password=self.password)
        data = {'page': 1, 'limit': 1, 'is_series': False, 'genre': '', 'sequels': False, 'rating': 15, 'year': ''}
        response = self.client.post(self.path, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(TitleCreationHistory.objects.filter(page=1, limit=1).exists())
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

        base_q = Title.objects.annotate(
            genres=ArrayAgg(
                'collection_titles__name', filter=Q(collection_titles__type=Collection.GENRE), distinct=True
            )
        ).select_related('poster', 'statistic')
        today = date.today()
        selections = {
            'releases': base_q.only('id', 'name', 'poster', 'premiere', 'type', 'statistic')
            .filter(premiere__lte=today)
            .order_by('-premiere')[:20],
            'most_viewed_titles': base_q.only('id', 'name', 'year', 'type', 'poster', 'statistic').order_by(
                '-statistic__views'
            )[:10],
            'upcoming_titles': base_q.only('id', 'name', 'poster', 'premiere', 'type', 'statistic')
            .filter(premiere__gt=today)
            .order_by('-premiere')[:20],
        }

        response = self.client.get(path)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['page_title'], 'MYANIMESITE | Онлайн кинотеатр')
        self.assertTemplateUsed(response, 'titles/index.html')
        self.assertEqual(list(response.context['most_viewed_titles']), list(selections['most_viewed_titles']))
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
            Title.objects.with_filmmakers()
            .prefetch_related(
                Prefetch(
                    'collection_titles',
                    queryset=Collection.objects.filter(type=Collection.GENRE),
                    to_attr='genres_prefetched',
                ),
                'persons',
                'studios',
            )
            .get(id=cls.title.id)
        )

    def setUp(self):
        types = {Title.SERIES: 'series', Title.MOVIE: 'movie'}
        self.params = lambda title: {'type': types[title.type], 'title_id': title.id}
        self.path = lambda params: reverse('titles:title_page', kwargs=params)

    def _common_tests(self, response, title):
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'titles/watch.html')
        self.assertEqual(response.context['page_title'], f'{title.name} | MYANIMESITE')

    @patch('titles.views.Title.external_urls', new_callable=PropertyMock)
    @patch('titles.views.get_partial_fill')
    @patch('titles.views.Title.objects.groupify')
    @patch('titles.views.Title.objects.similar_by_genres')
    def test_view_get(self, mock_similar, mock_groupify, mock_partial_fill, mock_external_urls):
        RatingHistory.objects.create(user=self.user, title=self.title, rating=8)

        self.client.login(username=self.username, password=self.password)

        mock_similar.return_value = self.related
        mock_groupify.return_value = self.group
        mock_partial_fill.return_value = {1: 100, 2: 100, 3: 0}
        mock_external_urls.return_value = ['url1', 'url2']

        path = self.path(self.params(self.title))
        response = self.client.get(path)

        self._common_tests(response, self.title)
        self.assertEqual(list(response.context['related']), list(self.related))
        self.assertEqual(list(response.context['group']), list(self.group))
        self.assertEqual(response.context['filled_star_rating'], mock_partial_fill.return_value)
        self.assertEqual(response.context['external_urls'], mock_external_urls.return_value)
        self.assertTrue(response.context['is_rated'])

        self.assertEqual(list(response.context['actors']), list(self.title.actors))
        self.assertEqual(list(response.context['directors']), list(self.title.directors))
        self.assertEqual(list(response.context['genres']), list(self.title.genres_prefetched))
        self.assertEqual(list(response.context['studios']), list(self.title.studios.all()))
        self.assertEqual(
            list(response.context['voiceovers']),
            list(
                VideoResource.objects.filter(content_unit__title=self.title).values_list('voiceover__name', flat=True)
            ),
        )

    @patch('titles.views.Title.external_urls', new_callable=PropertyMock)
    @patch('titles.views.Title.objects.groupify', return_value=[])
    @patch('titles.views.Title.objects.similar_by_genres', return_value=[])
    def test_view_get_when_title_has_minimal_content(self, mock_similar, mock_groupify, mock_external_urls):
        mock_external_urls.return_value = ['url1', 'url2']

        empty_title = Title.objects.exclude(id=self.title.id).first()

        path = self.path(self.params(empty_title))
        response = self.client.get(path)

        self._common_tests(response, empty_title)
        self.assertEqual(list(response.context['related']), [])
        self.assertEqual(list(response.context['group']), [])
        self.assertEqual(response.context['filled_star_rating'], {})
        self.assertEqual(response.context['external_urls'], mock_external_urls.return_value)
        self.assertFalse(response.context['is_rated'])

        self.assertIsNone(response.context['actors'])
        self.assertIsNone(response.context['directors'])
        self.assertEqual(list(response.context['genres']), [])
        self.assertEqual(list(response.context['studios']), [])
        self.assertEqual(list(response.context['voiceovers']), [])

    @patch('titles.views.Title.external_urls', new_callable=PropertyMock, return_value=[])
    @patch('titles.views.Title.objects.groupify', return_value=[])
    @patch('titles.views.Title.objects.similar_by_genres', return_value=[])
    def test_view_get_when_rating_history_does_not_exist(self, mock_similar, mock_groupify, mock_external_urls):
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
