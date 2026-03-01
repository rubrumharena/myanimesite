from http import HTTPStatus

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import TemplateView

from common.utils.tools import safe_int
from titles.models import Title
from video_player.models import VideoResource, ViewingHistory

# Create your views here.


# At present the view is interrupted by Django toolbar, so it can be called just 10 times per loading of a page.
# My tests say that everything is fine, so I think that it will work normally after switching to DEBUG=False
class VideoPlayerView(TemplateView):
    template_name = 'video_player/video_player.html'

    @staticmethod
    def _prepare_context(record, resource):
        if not resource and not record.has_record():
            return {'tracker': {}}

        if resource:
            tracker = record.get_independent_info(resource)
        else:
            tracker = record.get_user_info()

        return {'tracker': tracker}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        cur_record = ViewingHistory()
        try:
            episode, season, voiceover_id = (
                safe_int(self.request.GET.get('episode')),
                safe_int(self.request.GET.get('season')),
                safe_int(self.request.GET.get('voiceover_id')),
            )
        except ValueError:
            resource = VideoResource.objects.get_fallback(title=title, user=self.request.user)
            context.update(self._prepare_context(cur_record, resource))
            return context

        resource = None
        user = self.request.user
        if user.is_authenticated:
            record = (
                ViewingHistory.objects.filter(user=user, resource__content_unit__title=title)
                .order_by('-watched_at')
                .select_related('resource')
                .first()
            )
            cur_record = record if record else cur_record

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
        elif not cur_record.has_record():
            resource = VideoResource.objects.get_fallback(title=title, user=user)

        context.update(self._prepare_context(cur_record, resource))
        return context

    def get(self, request, *args, **kwargs):
        html = render_to_string(self.template_name, self.get_context_data(), request=request)
        return JsonResponse(data={'html': html}, status=HTTPStatus.OK)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(data={}, status=HTTPStatus.FORBIDDEN)

        data = request.POST

        try:
            position = safe_int(data.get('position', 0))
            episode, season, voiceover_id = (
                safe_int(data.get('episode')),
                safe_int(data.get('season')),
                safe_int(data.get('voiceover_id')),
            )

            if position < 0 or position is None:
                raise ValueError
        except ValueError:
            return JsonResponse(data={}, status=HTTPStatus.BAD_REQUEST)

        resource = VideoResource.objects.resolve_resource(
            episode=episode,
            season=season,
            voiceover_id=voiceover_id,
            title_id=self.kwargs.get('title_id'),
        )

        if not resource:
            return JsonResponse(data={}, status=HTTPStatus.NOT_FOUND)

        ViewingHistory.objects.update_or_create(user=request.user, resource=resource, defaults={'position': position})

        return JsonResponse(data={}, status=HTTPStatus.OK)
