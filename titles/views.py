from datetime import date
from decimal import Decimal
from http import HTTPStatus

from django.contrib.auth.decorators import user_passes_test
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView
from elasticsearch.dsl import Q as ES_Q

from comments.forms import CommentForm
from common.utils.enums import ChartType
from common.utils.ui import get_partial_fill
from common.utils.validators import check_single_rating_part
from common.utils.wrappers import login_required_ajax, superuser_required
from common.views.mixins import FolderFormMixin, PageTitleMixin
from lists.models import Collection
from services.kinopoisk_import import create_movie_objs, data_initialization
from titles.documents import TitleDocument
from titles.forms import TitleForm
from titles.models import RatingHistory, Statistic, Title, TitleCreationHistory
from video_player.models import VideoResource

# Create your views here.


class IndexView(PageTitleMixin, FolderFormMixin, TemplateView):
    template_name = 'titles/index.html'
    page_title = 'MYANIMESITE | Онлайн кинотеатр'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_q = Title.objects.annotate(
            genres=ArrayAgg('collections__name', filter=Q(collections__type=Collection.GENRE), distinct=True)
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

        charts = {
            'POPULAR': ChartType.POPULAR.value,
            'RATED': ChartType.RATED.value,
            'DISCUSSED': ChartType.DISCUSSED.value,
        }
        return {**context, **selections, 'charts': charts}


class TitleDetailView(PageTitleMixin, FolderFormMixin, DetailView):
    model = Title
    template_name = 'titles/watch.html'
    slug_field = 'pk'
    slug_url_kwarg = 'title_id'
    paginate_by = 2

    def get_queryset(self):
        return super().get_queryset().prefetch_related('backdrops').select_related('poster', 'statistic')

    def dispatch(self, request, *args, **kwargs):
        types = {Title.SERIES: 'series', Title.MOVIE: 'movie'}
        try:
            title_id = int(kwargs['title_id'])
            if title_id <= 0 or self.kwargs['type'] not in types.values():
                raise Http404
            self.object = self.get_object()
        except (ValueError, TypeError, ObjectDoesNotExist):
            raise Http404

        if self.kwargs['type'] != types[self.object.type]:
            return HttpResponseRedirect(
                reverse('titles:title_page', kwargs={'type': types[self.object.type], 'title_id': self.object.pk})
            )
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=...):
        title = (
            Title.objects.with_filmmakers()
            .prefetch_related(
                Prefetch(
                    'collections',
                    queryset=Collection.objects.filter(type=Collection.GENRE),
                    to_attr='genres_prefetched',
                ),
                'studios',
                'backdrops',
            )
            .select_related('statistic', 'poster')
            .get(id=self.kwargs.get('title_id'))
        )
        return title

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        title_obj = self.object
        title_id = title_obj.id
        genres = title_obj.genres_prefetched
        related = Title.objects.similar_by_genres(title_id)
        group = Title.objects.groupify(title_id)
        voiceovers = (
            VideoResource.objects.filter(content_unit__title=title_obj)
            .values_list('voiceover__name', flat=True)
            .distinct()
        )

        try:
            filled_star_rating = get_partial_fill(title_obj.statistic.rating)
            is_rated = (
                RatingHistory.objects.filter(user=self.request.user, title=title_obj).exists()
                if self.request.user.is_authenticated
                else False
            )
        except ObjectDoesNotExist:
            filled_star_rating, is_rated = {}, False

        return {
            **context,
            'actors': title_obj.actors,
            'directors': title_obj.directors,
            'studios': title_obj.studios.all(),
            'genres': genres,
            'voiceovers': voiceovers,
            'related': related,
            'group': group,
            'external_urls': title_obj.external_urls,
            'filled_star_rating': filled_star_rating,
            'is_rated': is_rated,
            'page_title': f'{title_obj.name} | MYANIMESITE',
            'comment_form': CommentForm(),
        }


@user_passes_test(superuser_required, login_url=reverse_lazy('admin:login'))
def bulk_title_generator_view(request):
    if request.method == 'POST':
        form = TitleForm(data=request.POST)
        if form.is_valid():
            form.save()

            creation_candidates, candidate_ids = data_initialization(configuration=form.cleaned_data)
            if creation_candidates:
                create_movie_objs(data_to_create=creation_candidates, title_ids=candidate_ids)
    else:
        form = TitleForm()
    history = TitleCreationHistory.objects.all().order_by('-created_at')
    context = {'form': form, 'history': history, 'page_title': 'Новые тайтлы | MYANIMESITE'}
    return render(request, 'titles/title_generator.html', context)


def search_ajax(request):
    search_field = request.GET.get('search_field')
    types = {Title.SERIES: 'series', Title.MOVIE: 'movie'}

    data = {'items': []}
    if search_field:
        q = ES_Q(
            'bool',
            should=[
                ES_Q('multi_match', query=search_field, fields=['name', 'alternative_name', 'names'], fuzziness='AUTO'),
                ES_Q(
                    'multi_match',
                    query=search_field,
                    fields=['name', 'alternative_name', 'names'],
                    type='phrase_prefix',
                ),
            ],
        )
        items = TitleDocument.search().query(q).to_queryset()

        for item in items:
            try:
                poster = item.poster.small.url
            except (AttributeError, ValueError, ObjectDoesNotExist):
                poster = None

            data['items'].append(
                {
                    'id': item.id,
                    'name': item.name,
                    'year': item.year,
                    'image': poster,
                    'genres': [genre.name for genre in item.collections.filter(type=Collection.GENRE).distinct()],
                    'type': item.type,
                    'url': reverse('titles:title_page', kwargs={'type': types[item.type], 'title_id': item.id}),
                }
            )

    elif search_field is None:
        return JsonResponse(data, status=HTTPStatus.BAD_REQUEST)
    return JsonResponse(data, status=HTTPStatus.OK)


@require_POST
@login_required_ajax
def set_rating_ajax(request):
    data = request.POST
    try:
        rating = Decimal(check_single_rating_part(float(data.get('rating'))))
        title_id = int(data.get('title_id'))
        statistics = Statistic.objects.get(title_id=title_id)
        prev_rating = RatingHistory.objects.get(user=request.user, title_id=title_id).rating
    except (ValueError, TypeError, ValidationError):
        return JsonResponse(data={}, status=HTTPStatus.BAD_REQUEST)
    except Statistic.DoesNotExist:
        return JsonResponse(data={}, status=HTTPStatus.NOT_FOUND)
    except RatingHistory.DoesNotExist:
        prev_rating = None

    obj, created = RatingHistory.objects.update_or_create(
        user=request.user, title_id=title_id, defaults={'rating': rating}
    )

    if created:
        total_rating = statistics.rating * statistics.votes
        statistics.votes += 1
    else:
        total_rating = statistics.rating * statistics.votes - prev_rating

    statistics.rating = (total_rating + rating) / statistics.votes
    statistics.save()
    return JsonResponse(data={'rating': f'{statistics.rating:.2f}', 'votes': statistics.votes}, status=HTTPStatus.OK)


def get_chart_ajax(request):
    data = {'items': []}
    chart_type = request.GET.get('type')

    base_q = (
        Title.objects.annotate(
            genres=ArrayAgg('collections__name', filter=Q(collections__type=Collection.GENRE), distinct=True)
        )
        .only('id', 'name', 'type', 'year', 'poster', 'statistic')
        .select_related('poster', 'statistic')
    )
    match chart_type:
        case ChartType.POPULAR.value:
            titles = base_q.order_by('-statistic__views')[:10]
        case ChartType.RATED.value:
            titles = base_q.order_by('-statistic__kp_rating')[:10]
        case ChartType.DISCUSSED.value:
            titles = base_q.annotate(comment_count=Count('comments', distinct=True)).order_by('-comment_count')[:10]
        case _:
            return JsonResponse(data=data, status=HTTPStatus.NOT_FOUND)

    types = {Title.SERIES: 'series', Title.MOVIE: 'movie'}
    data['items'] = [
        {
            'id': title.id,
            'url': reverse('titles:title_page', kwargs={'type': types.get(title.type, 'null'), 'title_id': title.id}),
            'name': title.name,
            'type': title.type,
            'year': title.year,
            'genres': title.genres,
            'small_poster': getattr(getattr(getattr(title, 'poster', None), 'small', None), 'url', None),
            'medium_poster': getattr(getattr(getattr(title, 'poster', None), 'medium', None), 'url', None),
            'views': title.statistic.views if chart_type == ChartType.POPULAR.value else 0,
            'rating': f'{title.statistic.kp_rating:.2f}' if chart_type == ChartType.RATED.value else 0,
            'comments': title.comment_count if chart_type == ChartType.DISCUSSED.value else 0,
        }
        for title in titles
    ]

    return JsonResponse(data, status=HTTPStatus.OK)


#
#
# @transaction.atomic
# def generate_best_movies(collection, limit=None):
#     collection_obj = OfficialCollection.objects.get(name=collection)
#     if collection_obj:
#         new_collection = set(Media.objects.filter(statistic__kp_rating__gte=7, type=collection_obj.type).order_by('-statistic__kp_rating')[:limit if limit else None])
#         old_collection = set(Media.objects.filter(mediacollectionlink_media__collection=collection_obj))
#
#         to_add = new_collection.difference(old_collection)
#         to_delete = old_collection.difference(new_collection)
#
#         Media.collections.through.objects.bulk_create([Media.collections.through(media=media, collection=collection_obj)
#                                                  for media in to_add])
#         Media.collections.through.objects.filter(media__in=to_delete, collection=collection_obj).delete()
