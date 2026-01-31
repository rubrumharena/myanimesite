from django.db import models
from django.db.models import Max

from common.utils.enums import EpisodeTracker
from titles.models import SeasonsInfo, Title

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

    def has_record(self):
        return self.id is not None

    @staticmethod
    def get_fallback(title):
        episode_tracker = EpisodeTracker()

        seasons = list(
            SeasonsInfo.objects.filter(title=title, season__isnull=False)
            .values('season')
            .annotate(max_episode=Max('episode'))
            .order_by('season')
        )
        if not seasons:
            return episode_tracker

        episode_count = seasons[0]['max_episode']

        episode_tracker.cur_season = seasons[0]['season']
        episode_tracker.episodes = (
            list(range(1, episode_count + 1)) if episode_count is not None and episode_count >= 1 else []
        )
        episode_tracker.seasons = [season['season'] for season in seasons]

        return episode_tracker

    def get_track_info(self, resource=None, title=None):
        episode_tracker = EpisodeTracker()
        if not resource and not self.has_record():
            if not title:
                raise ValueError('No title or resource provided to get_track_info')
            return self.get_fallback(title).__dict__

        resource = resource or self.resource
        title = resource.content_unit.title

        if title.type == Title.SERIES:
            episode_tracker.cur_season = resource.content_unit.season
            episode_tracker.cur_episode = resource.content_unit.episode
        episode_tracker.cur_voiceover = resource.voiceover_id
        episode_tracker.video = resource.iframe
        episode_tracker.time = self.position if self.has_record() else 0
        episode_tracker.voiceovers = list(
            VideoResource.objects.filter(content_unit=resource.content_unit, voiceover__isnull=False).values(
                'voiceover_id', 'voiceover__name'
            )
        )
        if title.type == Title.MOVIE:
            return episode_tracker.__dict__

        seasons = list(
            SeasonsInfo.objects.filter(title=title, season__isnull=False)
            .values('season')
            .annotate(max_episode=Max('episode'))
            .order_by('season')
        )
        if not seasons:
            return episode_tracker.__dict__

        episode_count = 0
        for season in seasons:
            if season['season'] == episode_tracker.cur_season:
                episode_count = season['max_episode']
                break

        episode_tracker.episodes = (
            list(range(1, episode_count + 1)) if episode_count is not None and episode_count >= 1 else []
        )
        episode_tracker.seasons = [season['season'] for season in seasons]
        episode_tracker.available_episodes = list(
            VideoResource.objects.filter(
                content_unit__title=title,
                content_unit__season=episode_tracker.cur_season,
                voiceover_id=episode_tracker.cur_voiceover,
            ).values_list('content_unit__episode', flat=True)
        )
        episode_tracker.available_seasons = list(
            VideoResource.objects.filter(content_unit__title=title, voiceover_id=episode_tracker.cur_voiceover)
            .values_list('content_unit__season', flat=True)
            .distinct()
        )
        return episode_tracker.__dict__
