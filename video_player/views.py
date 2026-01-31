from http import HTTPStatus

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from common.utils.tools import safe_int
from titles.models import Title
from video_player.models import VideoResource, ViewingHistory

# Create your views here.


class VideoPlayerAjaxView(View):
    def get(self, request, *args, **kwargs):
        title = get_object_or_404(Title, id=kwargs.get('title_id'))
        episode, season, voiceover_id = (
            request.GET.get('episode'),
            request.GET.get('season'),
            request.GET.get('voiceover'),
        )

        try:
            episode = safe_int(episode)
            season = safe_int(season)
            voiceover_id = safe_int(voiceover_id)
        except ValueError:
            resource = VideoResource.objects.get_fallback(title=title)
            return JsonResponse(
                data=ViewingHistory.get_track_info(resource, title),
                status=HTTPStatus.OK,
            )
        except TypeError:
            ...

        content = None
        resource = None
        viewing_record = ViewingHistory()
        user = request.user
        if user.is_authenticated:
            viewing_record = (
                ViewingHistory.objects.filter(user=user, resource__content_unit__title=title)
                .order_by('-watched_at')
                .select_related('resource')
                .first()
            ) or ViewingHistory()

        request_for_series = (episode or season or voiceover_id) and title.type == Title.SERIES
        request_for_movie = (not (episode or season) and voiceover_id) and title.type == Title.MOVIE

        if request_for_series or request_for_movie:
            resource = VideoResource.objects.resolve_resource(
                episode=episode,
                season=season,
                voiceover_id=voiceover_id,
                title_id=title.id,
            )
            if not resource:
                resource = VideoResource.objects.get_fallback(title=title, user=user)
        elif viewing_record.has_record():
            content = viewing_record.get_track_info()
        else:
            resource = VideoResource.objects.get_fallback(title=title, user=user)

        if not content:
            viewing_record = (
                (
                    (ViewingHistory.objects.filter(user=user, resource=resource).select_related('resource').first())
                    or ViewingHistory()
                )
                if resource and user.is_authenticated
                else ViewingHistory()
            )
            content = viewing_record.get_track_info(resource, title)

        return JsonResponse(data=content, status=HTTPStatus.OK)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(data={}, status=HTTPStatus.FORBIDDEN)

        data = request.POST
        episode, season, voiceover_id = (
            data.get('episode'),
            data.get('season'),
            data.get('voiceover'),
        )

        try:
            position = data.get('position', 0)
            episode = safe_int(episode)
            season = safe_int(season)
            voiceover_id = safe_int(voiceover_id)
            position = int(position) if position else 0
            if position < 0:
                raise ValueError
        except ValueError:
            return JsonResponse(data={}, status=HTTPStatus.BAD_REQUEST)
        except TypeError:
            ...

        resource = VideoResource.objects.resolve_resource(
            episode=episode,
            season=season,
            voiceover_id=voiceover_id,
            title_id=data.get('title_id'),
        )
        if not resource:
            return JsonResponse(data={}, status=HTTPStatus.NOT_FOUND)

        ViewingHistory.objects.update_or_create(user=request.user, resource=resource, defaults={'position': position})
        return_data = {
            'season': season,
            'voiceover': voiceover_id,
            'episode': episode,
            'position': position,
        }
        return JsonResponse(data=return_data, status=HTTPStatus.OK)
