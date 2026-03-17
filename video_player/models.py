from typing import TYPE_CHECKING, Any

from django.core.cache import cache
from django.db import models
from django.db.models import Max
from django.utils import timezone

from common.utils.cache_keys import VideoPlayerCacheKey
from titles.models import SeasonsInfo, Title

if TYPE_CHECKING:
    from common.utils.types import EpisodeTracker


# Create your models here.


class VoiceOver(models.Model):
    name = models.CharField(max_length=100, unique=True)


class VideoResource(models.Model):
    from common.models.querysets import VideoResourceQuerySet

    iframe = models.URLField()
    voiceover = models.ForeignKey('VoiceOver', on_delete=models.SET_NULL, null=True)
    content_unit = models.ForeignKey('titles.SeasonsInfo', on_delete=models.CASCADE)

    objects = VideoResourceQuerySet.as_manager()

    class Meta:
        unique_together = ('voiceover', 'content_unit')


class ViewingHistory(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    resource = models.ForeignKey('VideoResource', on_delete=models.CASCADE)
    watched_at = models.DateTimeField(auto_now=True)
    completed = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'resource')

    def has_record(self) -> bool:
        return self.id is not None

    def get_user_info(self) -> dict[str, Any]:
        return self._build_track_info(self.resource, self.position)

    def get_independent_info(self, resource: VideoResource) -> dict[str, Any]:
        return self._build_track_info(resource)

    @staticmethod
    def _build_base_track_info(tracker: 'EpisodeTracker', resource: VideoResource, position: int) -> None:
        unit = resource.content_unit
        cache_key = VideoPlayerCacheKey(unit.title_id, resource.voiceover_id, unit.season)

        tracker.cur_voiceover_id = resource.voiceover_id
        tracker.time = position

        voiceovers = cache.get(cache_key.voiceovers())
        if voiceovers is None:
            voiceover_ids = list(
                VideoResource.objects.filter(content_unit=resource.content_unit, voiceover__isnull=False).values_list(
                    'voiceover_id', flat=True
                )
            )
            voiceovers = VoiceOver.objects.filter(id__in=voiceover_ids)
            cache.set(cache_key.voiceovers(), voiceovers, 60**2 * 24)
        tracker.voiceovers = voiceovers
        tracker.video = resource.iframe

    @staticmethod
    def _build_series_track_info(tracker: 'EpisodeTracker', resource: VideoResource) -> None:
        unit = resource.content_unit
        title_id = unit.title_id
        cache_key = VideoPlayerCacheKey(unit.title_id, resource.voiceover_id, unit.season)
        seasons_cache_key = cache_key.seasons()
        av_seasons_cache_key = cache_key.available_seasons()
        av_episodes_cache_key = cache_key.available_episodes()

        tracker.cur_season = unit.season
        tracker.cur_episode = unit.episode

        seasons = cache.get(seasons_cache_key)
        if seasons is None:
            seasons = list(
                SeasonsInfo.objects.filter(title_id=title_id, season__isnull=False)
                .values('season')
                .annotate(max_episode=Max('episode'))
                .order_by('season')
            )
            cache.set(seasons_cache_key, seasons, 60**2 * 24)
        if not seasons:
            return

        episode_count = 0
        for season in seasons:
            if season['season'] == tracker.cur_season:
                episode_count = season['max_episode']
                break

        tracker.episodes = list(range(1, episode_count + 1)) if episode_count is not None and episode_count >= 1 else []
        tracker.seasons = [season['season'] for season in seasons]

        av_episodes = cache.get(av_episodes_cache_key)
        if av_episodes is None:
            av_episodes = list(
                VideoResource.objects.filter(
                    content_unit__title_id=title_id,
                    content_unit__season=tracker.cur_season,
                    voiceover_id=tracker.cur_voiceover_id,
                ).values_list('content_unit__episode', flat=True)
            )
            cache.set(av_episodes_cache_key, av_episodes, 60**2 * 24)

        av_seasons = cache.get(av_seasons_cache_key)
        if av_seasons is None:
            av_seasons = list(
                VideoResource.objects.filter(content_unit__title_id=title_id, voiceover_id=tracker.cur_voiceover_id)
                .values_list('content_unit__season', flat=True)
                .distinct()
            )
            cache.set(av_seasons_cache_key, av_seasons, 60**2 * 24)
        tracker.available_episodes = av_episodes
        tracker.available_seasons = av_seasons

    def _build_track_info(self, resource: VideoResource, position: int = 0) -> dict[str, Any]:
        from common.utils.types import EpisodeTracker

        tracker = EpisodeTracker()

        title = resource.content_unit.title
        self._build_base_track_info(tracker, resource, position)

        if title.type == Title.SERIES:
            self._build_series_track_info(tracker, resource)

        return tracker.__dict__


class Bucket(models.Model):
    title = models.ForeignKey('titles.Title', on_delete=models.CASCADE, related_name='bucket')
    date = models.DateField(default=timezone.localdate)
    views = models.PositiveIntegerField(default=0)

    def increment_views(self):
        self.views += 1
        self.save()

    class Meta: ...
