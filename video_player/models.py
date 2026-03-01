from typing import Any, TYPE_CHECKING

from django.db import models
from django.db.models import Max

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
        tracker.cur_voiceover_id = resource.voiceover_id
        tracker.video = resource.iframe
        tracker.time = position
        voiceover_ids = list(
            VideoResource.objects.filter(content_unit=resource.content_unit, voiceover__isnull=False).values_list(
                'voiceover_id', flat=True
            )
        )
        tracker.voiceovers = VoiceOver.objects.filter(id__in=voiceover_ids)

    @staticmethod
    def _build_series_track_info(tracker: 'EpisodeTracker', resource: VideoResource, title: Title) -> None:
        tracker.cur_season = resource.content_unit.season
        tracker.cur_episode = resource.content_unit.episode
        seasons = list(
            SeasonsInfo.objects.filter(title=title, season__isnull=False)
            .values('season')
            .annotate(max_episode=Max('episode'))
            .order_by('season')
        )
        if not seasons:
            return

        episode_count = 0
        for season in seasons:
            if season['season'] == tracker.cur_season:
                episode_count = season['max_episode']
                break

        tracker.episodes = list(range(1, episode_count + 1)) if episode_count is not None and episode_count >= 1 else []
        tracker.seasons = [season['season'] for season in seasons]
        tracker.available_episodes = list(
            VideoResource.objects.filter(
                content_unit__title=title,
                content_unit__season=tracker.cur_season,
                voiceover_id=tracker.cur_voiceover_id,
            ).values_list('content_unit__episode', flat=True)
        )
        tracker.available_seasons = list(
            VideoResource.objects.filter(content_unit__title=title, voiceover_id=tracker.cur_voiceover_id)
            .values_list('content_unit__season', flat=True)
            .distinct()
        )

    def _build_track_info(self, resource: VideoResource, position: int = 0) -> dict[str, Any]:
        from common.utils.types import EpisodeTracker

        tracker = EpisodeTracker()

        title = resource.content_unit.title
        self._build_base_track_info(tracker, resource, position)

        if title.type == Title.SERIES:
            self._build_series_track_info(tracker, resource, title)

        return tracker.__dict__
