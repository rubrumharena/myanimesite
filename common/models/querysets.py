from typing import TYPE_CHECKING

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Prefetch, Q, QuerySet, Value
from django.db.models.functions import Cast, Coalesce

if TYPE_CHECKING:
    from titles.models import Title
    from users.models import User
    from video_player.models import VideoResource


class VideoResourceQuerySet(models.query.QuerySet):
    def get_fallback(self, title: 'Title', user: 'User') -> 'VideoResource | None':
        from video_player.models import ViewingHistory

        if user.is_authenticated:
            record = ViewingHistory.objects.filter(resource__content_unit__title=title, user=user).first()
            if record:
                return record.resource

        return (
            self.filter(content_unit__title=title, iframe__isnull=False)
            .order_by('content_unit__season', 'content_unit__episode', 'voiceover_id')
            .select_related('content_unit')
            .first()
        )

    def resolve_resource(
        self, voiceover_id: int, title_id: int, episode: int | None = None, season: int | None = None
    ) -> 'VideoResource | None':
        resource = None
        base_params = {'content_unit__title_id': title_id, 'voiceover_id': voiceover_id}
        if episode and season and voiceover_id:
            resource = self.filter(content_unit__season=season, content_unit__episode=episode, **base_params).first()
        elif season and voiceover_id:
            resource = self.filter(content_unit__season=season, **base_params).order_by('content_unit__episode').first()
        elif voiceover_id:
            resource = self.filter(**base_params).order_by('content_unit__season', 'content_unit__episode').first()
        return None if not resource else resource


class TitleQuerySet(models.query.QuerySet):
    KP_MIN_VOTES = 500
    KP_MIN_RATING = 7.0

    def with_genres(self, only_names: bool = False) -> 'QuerySet[Title | str]':
        from lists.models import Collection

        if only_names:
            query = self.annotate(
                genres=Coalesce(
                    ArrayAgg('collections__name', filter=Q(collections__type=Collection.GENRE), distinct=True),
                    Value([]),
                )
            )
        else:
            query = self.prefetch_related(
                Prefetch(
                    'collections',
                    queryset=Collection.objects.filter(type=Collection.GENRE),
                    to_attr='genres',
                ),
                'studios',
                'backdrops',
            )

        return query.select_related('statistic', 'poster').only('id', 'name', 'premiere', 'poster', 'statistic', 'type')

    def with_weighted_rating(self) -> 'QuerySet[Title]':
        from titles.models import Title

        if not self.exists():
            return Title.objects.none()

        average = self.aggregate(avg_rating=Avg('statistic__kp_rating'))['avg_rating'] or 0

        votes = F('statistic__kp_votes')
        rating = Coalesce(F('statistic__kp_rating'), Value(0))

        votes_limit = Q(statistic__kp_votes__gte=self.KP_MIN_VOTES)
        rating_limit = Q(statistic__kp_rating__gt=self.KP_MIN_RATING)

        rating_expr = (Cast(votes, FloatField()) / (Cast(votes, FloatField()) + self.KP_MIN_VOTES)) * rating + (
            self.KP_MIN_VOTES / (Cast(votes, FloatField()) + self.KP_MIN_VOTES)
        ) * average

        return (
            self.annotate(weighted_rating=ExpressionWrapper(rating_expr, output_field=FloatField()))
            .filter(votes_limit & rating_limit)
            .order_by('-weighted_rating')
        )

    def count_best_titles(self) -> int:
        votes_limit = Q(statistic__kp_votes__gte=self.KP_MIN_VOTES)
        rating_limit = Q(statistic__kp_rating__gt=self.KP_MIN_RATING)

        return self.filter(votes_limit & rating_limit)[:20].count()

    def with_filmmakers(self) -> 'QuerySet[Title]':
        from titles.models import Person

        return self.annotate(
            actors=ArrayAgg('persons__name', distinct=True, filter=Q(persons__profession=Person.ACTOR)),
            directors=ArrayAgg('persons__name', distinct=True, filter=Q(persons__profession=Person.DIRECTOR)),
        )

    def similar_by_genres(self, title_id: int, limit: int = 20) -> 'QuerySet[Title]':
        from lists.models import Collection
        from titles.models import Title

        try:
            base_genres = (
                Title.objects.annotate(
                    genres=ArrayAgg('collections', distinct=True, filter=Q(collections__type=Collection.GENRE))
                )
                .get(id=title_id)
                .genres
            )
        except Title.DoesNotExist:
            return Title.objects.none()

        queryset = (
            Title.objects.filter(collections__type=Collection.GENRE)
            .exclude(id=title_id)
            .annotate(
                common_genres=Count('collections', filter=Q(collections__in=base_genres), distinct=True),
                total_genres=Count('collections', filter=Q(collections__type=Collection.GENRE), distinct=True),
            )
            .annotate(similarity=Cast('common_genres', FloatField()) / Cast('total_genres', FloatField()))
            .annotate(genres=ArrayAgg('collections__name', filter=Q(collections__type=Collection.GENRE), distinct=True))
            .select_related('poster', 'statistic')
            .order_by('-similarity')[:limit]
        )
        return queryset

    def groupify(self, title_id: int) -> 'QuerySet[Title]':
        return (
            self.filter(Q(children__child_id=title_id) | Q(children__parent_id=title_id))
            .select_related('statistic')
            .only('name', 'statistic', 'year', 'id', 'type')
            .distinct()
            .order_by('-year')
        )
