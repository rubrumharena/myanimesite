from datetime import date
from http import HTTPStatus

from django.contrib.auth.decorators import user_passes_test
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView
from elasticsearch.dsl import Q as ES_Q

from common.utils.enums import ChartType
from common.utils.validators import check_single_rating_part
from common.utils.wrappers import login_required_ajax, superuser_required
from common.views.mixins import PageTitleMixin
from services.kinopoisk_import import create_from_filters
from titles.documents import TitleDocument
from titles.forms import TitleForm
from titles.models import RatingHistory, Statistic, Title, TitleImportLog

# Create your views here.


class IndexView(PageTitleMixin, TemplateView):
    template_name = 'titles/index.html'
    page_title = 'MYANIMESITE | Онлайн кинотеатр'

    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_q = Title.objects.with_genres()
        today = date.today()
        selections = {
            'releases': base_q.filter(premiere__lte=today).order_by('-premiere')[:20],
            'upcoming_titles': base_q.filter(premiere__gt=today).order_by('-premiere')[:20],
        }

        charts = {chart.name: chart.value for chart in ChartType}
        return {**context, **selections, 'charts': charts}


class TitleDetailView(PageTitleMixin, DetailView):
    model = Title
    template_name = 'titles/watch.html'
    slug_field = 'id'
    slug_url_kwarg = 'title_id'

    def dispatch(self, request, *args, **kwargs):
        try:
            dispatch = super().dispatch(request, *args, **kwargs)

            title_id = int(kwargs['title_id'])
            if title_id <= 0 or self.kwargs['type'] not in [Title.SERIES, Title.MOVIE]:
                raise Http404

            if self.kwargs['type'] != self.object.type:
                return HttpResponseRedirect(
                    reverse('titles:title_page', kwargs={'type': self.object.type, 'title_id': self.object.id})
                )
        except (ValueError, TypeError, Title.DoesNotExist):
            raise Http404
        return dispatch

    def get_object(self, queryset=...):
        title_id = self.kwargs.get('title_id')
        cache_key = f'title_{title_id}'
        title = cache.get(cache_key)
        if title is None:
            title = Title.objects.with_filmmakers().with_genres(short=False).get(id=title_id)
            cache.set(cache_key, title, 60**2 * 24)
        return title

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        title_id = self.object.id
        cache_key = f'title_{title_id}'
        cache_rel_key = f'{cache_key}:related'
        cache_group_key = f'{cache_key}:group'

        related = cache.get(cache_rel_key)
        if related is None:
            related = Title.objects.similar_by_genres(title_id).with_genres()
            cache.set(cache_rel_key, related, 60**2 * 24)

        group = cache.get(cache_group_key)
        if group is None:
            group = Title.objects.groupify(title_id)
            cache.set(cache_group_key, group, 60**2 * 24)

        user = self.request.user
        is_rated = (
            RatingHistory.objects.filter(user=user, title_id=title_id).exists() if user.is_authenticated else False
        )

        return {
            **context,
            'related': related,
            'group': group,
            'is_rated': is_rated,
            'page_title': f'{self.object.name} | MYANIMESITE',
        }


class TitleGeneratorView(PageTitleMixin, TemplateView):
    page_title = 'Новые тайтлы | MYANIMESITE'
    template_name = 'titles/title_generator.html'

    @method_decorator(user_passes_test(superuser_required, login_url=reverse_lazy('admin:login')))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = TitleForm(data=request.POST)
        if form.is_valid():
            create_from_filters(form.cleaned_data)
            form.save()
            return HttpResponseRedirect(reverse('titles:title_generator'))

        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = kwargs.get('form', TitleForm())
        history = TitleImportLog.objects.order_by('-created_at')

        return {**context, 'form': form, 'history': history}


class SearchTitleView(TemplateView):
    template_name = 'titles/modules/_search.html'

    def get(self, request, *args, **kwargs):
        html = render_to_string(self.template_name, self.get_context_data(), request)
        return JsonResponse(data={'html': html}, status=HTTPStatus.OK)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_field = self.request.GET.get('search')

        titles = Title.objects.none()
        if search_field:
            q = ES_Q(
                'bool',
                should=[
                    ES_Q(
                        'multi_match',
                        query=search_field,
                        fields=['name', 'alternative_name', 'names'],
                        fuzziness='AUTO',
                    ),
                    ES_Q(
                        'multi_match',
                        query=search_field,
                        fields=['name', 'alternative_name', 'names'],
                        type='phrase_prefix',
                    ),
                ],
            )
            titles = TitleDocument.search().query(q).to_queryset().with_genres()

        return {**context, 'titles': titles}


class ChartView(TemplateView):
    template_name = 'titles/modules/_chart.html'

    def get(self, request, *args, **kwargs):
        html = render_to_string(self.template_name, self.get_context_data(), request)
        return JsonResponse(data={'html': html}, status=HTTPStatus.OK)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chart = self.kwargs['type']
        cache_key = f'chart_titles:{chart}'
        base_q = Title.objects.with_genres()

        titles = cache.get(cache_key)
        if titles is not None:
            context['titles'] = titles
        else:
            match chart:
                case ChartType.POPULAR.value:
                    titles = base_q.order_by('-statistic__views')[:10]
                case ChartType.RATED.value:
                    titles = base_q.order_by('-statistic__kp_rating')[:10]
                case ChartType.DISCUSSED.value:
                    titles = base_q.annotate(comment_count=Count('comments', distinct=True)).order_by('-comment_count')[
                        :10
                    ]
                case _:
                    raise Http404()
            cache.set(cache_key, titles, 60 * 15)
            context['titles'] = titles

        charts = {chart.name: chart.value for chart in ChartType}
        return {**context, 'chart': chart, 'charts': charts}


@require_POST
@login_required_ajax
def set_rating(request, rating, title_id):
    try:
        check_single_rating_part(rating)
        statistic = Statistic.objects.get(title_id=title_id)
        prev_rating = RatingHistory.objects.get(user=request.user, title_id=title_id).rating
    except ValidationError:
        return JsonResponse(data={}, status=HTTPStatus.BAD_REQUEST)
    except Statistic.DoesNotExist:
        return JsonResponse(data={}, status=HTTPStatus.NOT_FOUND)
    except RatingHistory.DoesNotExist:
        prev_rating = 0

    _, created = RatingHistory.objects.update_or_create(
        user=request.user, title_id=title_id, defaults={'rating': rating}
    )

    if created:
        total_rating = statistic.rating * statistic.votes
        statistic.votes += 1
    else:
        total_rating = statistic.rating * statistic.votes - prev_rating

    statistic.rating = (total_rating + rating) / statistic.votes
    statistic.save()
    return JsonResponse(data={'rating': statistic.rating, 'votes': statistic.votes}, status=HTTPStatus.OK)
