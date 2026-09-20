from datetime import date
from http import HTTPStatus
from urllib.parse import urlencode

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, F
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView
from elasticsearch.dsl import Q as ES_Q

from common.utils.cache_keys import TitlesCacheKey, cache_by_func, cached
from common.utils.enums import ChartType, CommentType
from common.utils.wrappers import login_required_ajax, superuser_required
from common.views.mixins import PageTitleMixin
from services.kinopoisk_import import create_from_filters
from titles.documents import TitleDocument
from titles.forms import StatusForm, TitleForm
from titles.models import LibraryEntry, Title, TitleImportLog

# Create your views here.


class IndexView(PageTitleMixin, TemplateView):
    template_name = 'titles/index.html'
    page_title = _('MYANIMESITE | Онлайн кинотеатр')

    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_q = Title.objects.with_genres()
        today = date.today()

        cache_key_r = TitlesCacheKey.releases()
        cache_key_ut = TitlesCacheKey.upcoming_titles()

        releases = cache_by_func(lambda: base_q.filter(premiere__lte=today).order_by('-premiere')[:20], cache_key_r)
        upcoming_titles = cache_by_func(
            lambda: base_q.filter(premiere__gt=today).order_by('-premiere')[:20], cache_key_ut
        )

        selections = {'releases': releases, 'upcoming_titles': upcoming_titles}

        charts = [{'url': reverse('titles:chart', args=[c.value]), 'name': c.label, 'slug': c.value} for c in ChartType]

        return {**context, **selections, 'charts': charts, 'cur_chart': ChartType.POPULAR.value}


class TitleDetailView(PageTitleMixin, DetailView):
    model = Title
    template_name = 'titles/watch.html'
    slug_field = 'id'
    slug_url_kwarg = 'title_id'
    form_prefix = 'single'

    def dispatch(self, request, *args, **kwargs):
        print('a')

        print('a1')
        dispatch = super().dispatch(request, *args, **kwargs)
        print('a2')
        title_id = int(kwargs['title_id'])
        print(title_id)
        if title_id <= 0 or self.kwargs['type'] not in [Title.SERIES, Title.MOVIE]:
            print('c')
            raise Http404

        if self.kwargs['type'] != self.object.type:
            return HttpResponseRedirect(
                reverse('titles:title_page', kwargs={'type': self.object.type, 'title_id': self.object.id})
            )

        print('b')

        return dispatch

    def get_object(self, queryset=...):
        title_id = self.kwargs.get('title_id')
        cache_key = TitlesCacheKey.title(title_id)
        title = cache_by_func(
            lambda: Title.objects.with_filmmakers().with_genres(short=False).get(id=title_id), cache_key
        )
        return title

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        title_id = self.object.id

        rel_cache_key = TitlesCacheKey.related_titles(title_id)
        group_cache_key = TitlesCacheKey.title_group(title_id)

        related = cache_by_func(lambda: Title.objects.similar_by_genres(title_id).with_genres(), rel_cache_key)
        group = cache_by_func(lambda: Title.objects.groupify(title_id), group_cache_key)

        status = None
        if self.request.user.is_authenticated:
            status = LibraryEntry.objects.filter(user=self.request.user, title_id=title_id).first()
            
        status_form = StatusForm(
            prefix=self.form_prefix,
            initial={
                'status': getattr(status, 'status', LibraryEntry.NOT_WATCHED),
            },
        )
        status_form.fields['status'].widget.title_id = title_id

        base = reverse('comments:comments', args=[title_id])
        comments = [
            {
                'url': f'{base}?{urlencode({"filter_by": c.value})}',
                'name': c.label,
                'slug': c.value,
            }
            for c in CommentType
        ]

        return {
            **context,
            'related': related,
            'group': group,
            'status_form': status_form,
            'page_title': f'{self.object.name} | MYANIMESITE',
            'comments': comments,
            'cur_com_type': CommentType.ALL.value,
        }


class TitleGeneratorView(PageTitleMixin, TemplateView):
    page_title = _('Новые тайтлы | MYANIMESITE')
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
    template_name = 'titles/modules/search.html'

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
    template_name = 'titles/modules/chart.html'

    def get(self, request, *args, **kwargs):
        html = render_to_string(self.template_name, self.get_context_data(), request)
        return JsonResponse(data={'html': html}, status=HTTPStatus.OK)

    @cached(lambda self: TitlesCacheKey.chart(self.kwargs['type']))
    def get_chart(self):
        chart = self.kwargs['type']
        base_q = Title.objects.with_genres()
        match chart:
            case ChartType.POPULAR.value:
                titles = base_q.annotate(chart_val=F('statistic__views'))
            case ChartType.RATED.value:
                titles = base_q.annotate(chart_val=F('statistic__kp_rating')).filter(statistic__kp_rating__isnull=False)
            case ChartType.DISCUSSED.value:
                titles = base_q.annotate(chart_val=Count('comments', distinct=True))
            case _:
                raise Http404()

        return titles.order_by('-chart_val')[:10]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titles'] = self.get_chart()
        charts = {chart.name: chart.value for chart in ChartType}
        return {**context, 'chart': self.kwargs['type'], 'charts': charts}


@require_POST
@login_required_ajax
def set_status(request, status, title_id):
    form = StatusForm(data={'title': title_id, 'status': status})

    if form.is_valid():
        obj, created = LibraryEntry.objects.update_or_create(
            user=request.user,
            title=form.cleaned_data['title'],
            defaults={'status': form.cleaned_data['status']},
        )
        return JsonResponse(data={'created': created}, status=HTTPStatus.OK)

    return JsonResponse(data={}, status=HTTPStatus.NOT_FOUND)
