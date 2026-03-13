from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone

from common.utils.testing_components import TestVideoPlayerSetUpMixin
from lists.models import Collection
from titles.models import Group, Person, Statistic, Title
from video_player.models import Bucket, VideoResource, ViewingHistory


class TitleQuerySetTestCase(TestCase):
    def setUp(self):
        titles = (Title(name=f'Title {i}', id=i, type=Title.MOVIE, year=i) for i in range(1, 5))
        Title.objects.bulk_create(titles)
        stats = [
            Statistic(kp_rating=8.5, kp_votes=600, title_id=1),
            Statistic(kp_rating=8.4, kp_votes=1500, title_id=4),
            Statistic(kp_rating=6, kp_votes=2000, title_id=2),
            Statistic(kp_rating=9, kp_votes=100, title_id=3),
        ]
        Statistic.objects.bulk_create(stats)
        self.queryset = Title.objects.all()

    def _set_up_with_filmmakers(self):
        actors = [Person(name=f'Actor {i}', profession=Person.ACTOR, kinopoisk_id=i, id=i) for i in range(15)]
        directors = [
            Person(name=f'Director {i}', profession=Person.DIRECTOR, kinopoisk_id=i, id=i) for i in range(100, 104)
        ]
        Person.objects.bulk_create(actors + directors)

        titles = Title.objects.all()[:3]

        limit = 0
        rels = []
        related_model = Title.persons.through
        for title, director in zip(titles, directors):
            for person in Person.objects.filter(profession=Person.ACTOR)[limit : limit + 5]:
                rels.append(related_model(title=title, person=person))
            rels.append(related_model(title=title, person=director))
            limit += 5
        related_model.objects.bulk_create(rels)

    def _set_up_collections(self):
        genres = (Collection(type=Collection.GENRE, name=f'Genre {i}', id=i) for i in range(1, 5))
        Collection.objects.bulk_create(genres)

        rels = []
        related_model = Title.collections.through
        genre_1 = Collection.objects.get(id=1)
        genre_2 = Collection.objects.get(id=2)
        genre_3 = Collection.objects.get(id=3)
        genre_4 = Collection.objects.get(id=4)

        title_1 = Title.objects.get(id=1)
        title_2 = Title.objects.get(id=2)
        title_3 = Title.objects.get(id=3)
        title_4 = Title.objects.get(id=4)

        rels.append(related_model(title=title_1, collection=genre_1))
        rels.append(related_model(title=title_4, collection=genre_1))
        rels.append(related_model(title=title_3, collection=genre_1))

        rels.append(related_model(title=title_1, collection=genre_2))
        rels.append(related_model(title=title_3, collection=genre_2))

        rels.append(related_model(title=title_1, collection=genre_3))

        rels.append(related_model(title=title_2, collection=genre_4))
        related_model.objects.bulk_create(rels)

    def _set_up_groups(self):
        rels = []
        title_1 = Title.objects.get(id=1)
        title_2 = Title.objects.get(id=2)
        title_3 = Title.objects.get(id=3)

        rels.append(Group(parent=title_1, child=title_2))
        rels.append(Group(parent=title_1, child=title_3))

        rels.append(Group(parent=title_2, child=title_1))
        rels.append(Group(parent=title_2, child=title_3))

        rels.append(Group(parent=title_3, child=title_1))
        rels.append(Group(parent=title_3, child=title_2))

        Group.objects.bulk_create(rels)

    def test_with_weighted_rating__happy_path(self):
        result = list(self.queryset.with_weighted_rating())

        self.assertEqual(result, [Title.objects.get(id=4), Title.objects.get(id=1)])

        self.assertNotIn(Title.objects.get(id=2), result)
        self.assertNotIn(Title.objects.get(id=3), result)

    def test_with_weighted_rating__if_queryset_is_none(self):
        queryset = Title.objects.none()
        result = list(queryset.with_weighted_rating())
        self.assertEqual(result, list(queryset))

    def test_count_best_titles__happy_path(self):
        self.assertEqual(self.queryset.count_best_titles(), 2)

    def test_count_best_titles__when_title_count_is_more_than_limit(self):
        self.queryset.delete()
        titles = (Title(name=f'Title {i}', id=i, type=Title.MOVIE) for i in range(30))
        Title.objects.bulk_create(titles)

        stats = []
        for title in Title.objects.all():
            stats.append(Statistic(kp_rating=10, kp_votes=1000, title_id=title.id))
        Statistic.objects.bulk_create(stats)

        queryset = Title.objects.all()
        self.assertEqual(queryset.count_best_titles(), 20)

    def test_with_filmmakers__happy_path(self):
        self._set_up_with_filmmakers()
        queryset = Title.objects.filter(persons__isnull=False).with_filmmakers()

        self.assertEqual(queryset.count(), 3)
        for title in queryset:
            self.assertEqual(len(title.actors), 5)
            self.assertEqual(len(title.directors), 1)
            self.assertTrue(all(name.startswith('Actor') for name in title.actors))
            self.assertTrue(all(name.startswith('Director') for name in title.directors))
            self.assertEqual(len(title.actors), len(set(title.actors)))
            self.assertEqual(len(title.directors), len(set(title.directors)))

    def test_similar_by_genres__happy_path(self):
        self._set_up_collections()
        title = Title.objects.get(id=1)
        title_2 = Title.objects.get(id=2)
        title_3 = Title.objects.get(id=3)
        title_4 = Title.objects.get(id=4)

        result = Title.objects.similar_by_genres(title.id)
        expected_result = [title_3, title_4, title_2]
        self.assertEqual(result.count(), 3)
        self.assertEqual(list(result), expected_result)

    def test_similar_by_genres__when_genres_different(self):
        genres = (Collection(type=Collection.GENRE, name=f'Genre {i}', id=i) for i in range(1, 5))
        Collection.objects.bulk_create(genres)
        title = Title.objects.get(id=1)

        titles = Title.objects.all()
        collections = Collection.objects.all()

        related_model = Title.collections.through
        rels = (related_model(title=title, collection=collection) for title, collection in zip(titles, collections))
        related_model.objects.bulk_create(rels)

        result = Title.objects.similar_by_genres(title.id)

        self.assertEqual(result.count(), 3)

    def test_groupify__happy_path(self):
        title = Title.objects.get(id=1)
        title_2 = Title.objects.get(id=2)
        title_3 = Title.objects.get(id=3)
        expected_result = [title_3, title_2, title]

        self._set_up_groups()
        result = Title.objects.groupify(title_id=title.id)

        self.assertEqual(result.count(), 3)
        self.assertEqual(list(result), expected_result)

    def test_groupify__when_no_children(self):
        title = Title.objects.get(id=1)

        result = Title.objects.groupify(title_id=title.id)

        self.assertEqual(result.count(), 0)

    def test_with_genres__when_collection_objects(self):
        self._set_up_collections()
        titles = Title.objects.filter(collections__isnull=False).distinct()[:2]
        model = Title.collections.through
        genres1 = [inst.collection for inst in model.objects.filter(title=titles[0])]
        genres2 = [inst.collection for inst in model.objects.filter(title=titles[1])]

        annotated_titles = titles.with_genres()
        self.assertEqual(list(annotated_titles[0].genres), genres1)
        self.assertEqual(list(annotated_titles[1].genres), genres2)

    def test_with_genres__when_collection_names(self):
        self._set_up_collections()
        titles = Title.objects.filter(collections__isnull=False).distinct()[:2]
        model = Title.collections.through
        genres1 = [inst.collection.name for inst in model.objects.filter(title=titles[0])]
        genres2 = [inst.collection.name for inst in model.objects.filter(title=titles[1])]

        annotated_titles = titles.with_genres(only_names=True)
        self.assertEqual(list(annotated_titles[0].genres), genres1)
        self.assertEqual(list(annotated_titles[1].genres), genres2)

    def test_with_genres__when_no_collections(self):
        title = Title.objects.create(name='Genre 999', id=999)
        titles = Title.objects.filter(id=title.id)

        annotated_titles = titles.with_genres(only_names=True)
        self.assertEqual(list(annotated_titles[0].genres), [])

        annotated_titles = titles.with_genres()
        self.assertEqual(list(annotated_titles[0].genres), [])

    def test_only_actual_titles__happy_path(self):
        today = timezone.localdate()
        titles = Title.objects.all()[:3]

        buckets1 = [Bucket(date=today - timedelta(i), title=titles[0], views=i) for i in range(1, 8)]
        buckets2 = [Bucket(date=today - timedelta(i), title=titles[1], views=i + 10) for i in range(1, 8)]
        buckets3 = [Bucket(date=today - timedelta(days=30), title=titles[2], views=i + 10) for i in range(1, 5)]
        Bucket.objects.bulk_create(buckets1 + buckets2 + buckets3)

        actual_titles = Title.objects.only_actual_titles()

        self.assertEqual(list(actual_titles), [titles[1], titles[0]])
        self.assertEqual(actual_titles[1].last_week_views, sum(range(1, 8)))
        self.assertEqual(actual_titles[0].last_week_views, sum(map(lambda num: num + 10, range(1, 8))))


class VideoResourceQuerySetTestCase(TestVideoPlayerSetUpMixin, TestCase):
    def test_get_fallback__when_user_has_saved_history(self):
        resource = VideoResource.objects.first()
        ViewingHistory.objects.create(user=self.user, resource=resource)
        self.assertEqual(
            resource, VideoResource.objects.get_fallback(title=resource.content_unit.title, user=self.user)
        )

    def test_get_fallback__when_user_does_not_has_saved_history(self):
        self.assertEqual(self.ser_resource1, VideoResource.objects.get_fallback(title=self.series, user=self.user))

    def test_get_fallback__when_user_is_unauthorized(self):
        self.assertEqual(
            self.ser_resource1, VideoResource.objects.get_fallback(title=self.series, user=AnonymousUser())
        )

    def test_resolve_resource__if_episode_season_and_voiceover(self):
        content = self.ser_resource1.content_unit
        self.assertEqual(
            self.ser_resource1,
            VideoResource.objects.resolve_resource(
                episode=content.episode,
                season=content.season,
                voiceover_id=self.ser_resource1.voiceover_id,
                title_id=content.title_id,
            ),
        )

    def test_resolve_resource__if_season_and_voiceover(self):
        content = self.ser_resource1.content_unit
        self.assertEqual(
            self.ser_resource1,
            VideoResource.objects.resolve_resource(
                season=content.season, voiceover_id=self.ser_resource1.voiceover_id, title_id=content.title_id
            ),
        )

    def test_resolve_resource__if_voiceover(self):
        content = self.ser_resource1.content_unit
        self.assertEqual(
            self.ser_resource1,
            VideoResource.objects.resolve_resource(
                voiceover_id=self.ser_resource1.voiceover_id, title_id=content.title_id
            ),
        )

    def test_resolve_resource__if_nothing_given(self):
        self.assertIsNone(VideoResource.objects.resolve_resource(voiceover_id=None, title_id=self.series.id))
