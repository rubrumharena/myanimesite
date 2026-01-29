from http import HTTPStatus
from urllib.parse import urlencode
from datetime import date
from functools import reduce, cached_property
from operator import and_
from typing import Dict, List, Iterable

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import ListView, FormView

from common.utils.enums import ListSortOption, ListQueryParam, ListQueryValue
from common.utils.ui import generate_years_and_decades
from common.utils.validators import validate_years
from common.views.mixins import FolderFormMixin, PaginatorMixin

from titles.models import Title
from lists.models import Collection
from video_player.models import ViewingHistory


class BaseListView(PaginatorMixin, FolderFormMixin, ListView):
    model = Title
    paginate_by = 32

    route = None
    _internal_queryset_call = False

    def get_queryset(self):
        query_params = ListQueryParam
        query_values = ListQueryValue
        query_filters = [Q()]
        path_params = self.kwargs.get('path_params')
        f_params = self.request.GET.getlist(query_params.FILTER.value)

        if path_params:
            cleaned_params = self.resolved_path_params
            genre, year, collection = (cleaned_params['genre']['slug'], cleaned_params['year']['slug'],
                                       cleaned_params['collection']['slug'],)

            query_filters.append(Q(collections__slug=collection) if collection else Q())
            query_filters.append(Q(collections__slug=genre) if genre else Q())

            if year:
                try:
                    validate_years(year)
                    query_filters.append(Q(year=year) if year.isdigit() else Q(year__range=year.split('-')))
                except ValidationError as _:
                    ...

        if f_params:
            user = self.request.user
            is_movie = query_values.MOVIES.value in f_params
            is_series = query_values.SERIES.value in f_params
            if is_movie and is_series:
                return Title.objects.none()

            if is_movie:
                query_filters.append(Q(type=Title.MOVIE))
            elif is_series:
                query_filters.append(Q(type=Title.SERIES))

            query_filters.append(Q(premiere__lte=date.today()) if query_values.RELEASED.value in f_params else Q())
            query_filters.append(Q(statistic__kp_rating__gte=7) if query_values.RATED.value in f_params else Q())
            if query_values.UNWATCHED.value in f_params and user.is_authenticated:
                watched_titles = ViewingHistory.objects.filter(user=user).distinct().values_list('resource__content_unit__title_id', flat=True)
                query_filters.append(~Q(id__in=watched_titles))

        queryset = (Title.objects
                    .annotate(genres=ArrayAgg('collections__name', filter=Q(collections__type=Collection.GENRE),
                                              distinct=True))
                    .select_related('poster', 'statistic')
                    .only('id', 'name', 'premiere', 'poster', 'statistic', 'type')
                    .filter(reduce(and_, query_filters))
                    .distinct())

        if self._internal_queryset_call:
            self._internal_queryset_call = False
            return queryset

        if self.request.GET.get(query_params.TAB.value) == query_values.BEST.value:
            queryset = queryset.filter(id__in=queryset.with_weighted_rating()[:20].values('id'))

        return queryset.order_by(self.sort_method)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_values = ListQueryValue
        query_params = ListQueryParam
        genres = Collection.objects.filter(type=Collection.GENRE).values('name', 'slug')
        years = [{'name': year, 'slug': year} for year in generate_years_and_decades()]

        self._internal_queryset_call = True
        object_list = self.get_queryset()

        return {**context,
                'sort_methods': {option.value: option.label for option in ListSortOption},
                'params': {param.name: param.value for param in query_params},
                'query_values': {value.name: value.value for value in query_values},

                'genre_filters': self.prepare_list_filter_items(genres, query_params.GENRES.value),
                'year_filters': self.prepare_list_filter_items(years, query_params.YEARS.value),

                'flags': self.prepare_flags(object_list),
                'filter_urls': self.filter_switch_urls,
                'path_params': self.resolved_path_params,

                'all_titles_count': object_list.count(),
                'best_titles_count': object_list.count_best_titles()}

    @cached_property
    def resolved_path_params(self) -> Dict[str, Dict[str, str]]:
        path_params = self.kwargs.get('path_params')
        is_folder = self.kwargs.get('folder_id') is not None

        param_names = ['genre', 'year']

        parsed_params = {param: {'slug': '', 'url': ''} for param in param_names + ['collection']}
        collections = set(
            Collection.objects.filter(type__in=(Collection.MOVIE_COLLECTION, Collection.SERIES_COLLECTION)).values_list(
                'slug', flat=True))
        if path_params:
            separator = '--'
            unparsed_params = path_params.split('/')

            for i, segment in enumerate(unparsed_params):
                is_collection = segment in collections and i == 0
                is_separated = separator in segment

                if (not is_separated and not is_collection) or (is_folder and is_collection):
                    raise Http404
                elif is_collection:
                    parsed_params['collection']['slug'] = segment
                    parsed_params['genre']['url'] = segment
                    parsed_params['year']['url'] = segment
                    continue

                param, value = segment.split(separator, maxsplit=1)
                param_count = path_params.count(param + separator)
                if param not in param_names or not value or param_count > 1:
                    raise Http404

                parsed_params[param] = {'slug': value, 'url': '/'.join(
                    raw_param for raw_param in unparsed_params if raw_param != segment)}

                for name in param_names:
                    url = parsed_params[name]['url']
                    if name != param and segment not in url:
                        parsed_params[name]['url'] += f'/{segment}' if url else segment

        return parsed_params

    @property
    def filter_switch_urls(self) -> Dict[str, str]:
        # This is a quite hard to understand method to solve two filtering cases:
        # 1) When it is any parameter but movies or series, it should create link for itself without itself,
        # and with itself for others;
        # 2) When it movies or series parameter, it should create link like above, but it cannot be movies and series in time.

        f_param = ListQueryParam.FILTER.value
        query_values = ListQueryValue
        params = dict(self.request.GET.lists())
        params.pop(ListQueryParam.PAGE.value, None)
        f_params = params.get(f_param, [])
        urls = {}

        toggle_pairs = {query_values.MOVIES.value: query_values.SERIES.value,
                        query_values.SERIES.value: query_values.MOVIES.value}
        if not all(f_params):
            f_params = list(filter(None, f_params))

        for cur_param in query_values.get_f_params():
            cur_param = cur_param.value

            if cur_param in f_params:
                params[f_param] = [param for param in f_params if param != cur_param]
            else:
                params[f_param] = f_params + [cur_param]

            toggled_param = toggle_pairs.get(cur_param)
            if toggled_param in f_params:
                params[f_param].remove(toggled_param)

            url = urlencode(params, doseq=True)
            urls[cur_param] = self.request.path + ('?' + url if url else '')
        return urls

    @property
    def sort_method(self) -> str:
        option = ListSortOption
        match self.request.GET.get('sort'):
            case option.VOTES.value:
                sort_method = '-statistic__kp_votes'
            case option.RATING.value:
                sort_method = '-statistic__kp_rating'
            case option.NAME.value:
                sort_method = 'name'
            case option.PREMIERE.value:
                sort_method = '-premiere'
            case _:
                sort_method = 'created_at'

        return sort_method

    @staticmethod
    def generate_collection_title(path_params: Dict[str, Dict[str, str]], f_params: List[str]) -> str:
        collection = path_params['collection']['slug']

        if collection:
            return Collection.objects.get(slug=collection).name
        values = ListQueryValue

        type_part = ''
        is_movies = values.MOVIES.value in f_params
        is_series = values.SERIES.value in f_params
        if is_movies and is_series or not (is_movies or is_series):
            type_part = 'аниме фильмы и сериалы'
        elif values.SERIES.value in f_params:
            type_part = 'аниме сериалы'
        elif values.MOVIES.value in f_params:
            type_part = 'аниме фильмы'

        year_part = ''
        year = path_params['year']['slug']
        if year:
            year_part = f' {year} года' if year.isdigit() else f' {year[:4]}-х годов'

        genre = path_params['genre']['slug']
        if genre:
            title = Collection.objects.get(slug=genre).name + year_part + f' - {type_part}'
        else:
            title = type_part + year_part

        return title.strip().capitalize()

    def prepare_flags(self, object_list: Iterable) -> Dict[str, bool]:
        query_values = ListQueryValue
        query_params = ListQueryParam
        f_params = self.request.GET.getlist(query_params.FILTER.value)

        is_movies = query_values.MOVIES.value in f_params
        is_series = query_values.SERIES.value in f_params

        return {
            'movies': is_movies,
            'series': is_series,
            'released': query_values.RELEASED.value in f_params,
            'unwatched': query_values.UNWATCHED.value in f_params,
            'rated': query_values.RATED.value in f_params,
            'blocked': (is_movies and is_series) or not object_list,
        }

    def prepare_list_filter_items(self, items: Iterable[Dict[str, str]], prefix: str) -> List[Dict[str, str]]:
        if prefix not in (ListQueryParam.YEARS.value, ListQueryParam.GENRES.value):
            raise Http404
        path_params = self.resolved_path_params

        slug = path_params[prefix]['slug']
        url = path_params[prefix]['url']
        root_url = self.route + url + ('/' if url else '')

        data = [{'url': root_url, 'is_selected': True if not slug else False, 'name': 'Любой'}]
        for item in items:
            item_slug = item['slug']
            url = root_url + f'{prefix}--{item_slug}/'
            data.append({'url': url, 'is_selected': slug == item_slug, 'name': item['name']})
        return data


class BaseSettingsView(LoginRequiredMixin, View):
    template_name = ''
    form_map = {}

    def get_forms(self, active_form=None):
        forms = {
            name: self.build_form(form_class, isinstance(active_form, form_class))
            for name, form_class in self.form_map.items()
        }

        if active_form:
            for name, form in forms.items():
                if isinstance(active_form, form.__class__):
                    forms[name] = active_form
        return forms

    def build_form(self, form_class, data_required=True):
        raise NotImplementedError

    def form_valid(self, form_name, form):
        form.save()
        return self.get(self.request)

    def form_invalid(self, form):
        html = render_to_string(
            self.template_name,
            self.get_forms(form),
            self.request
        )
        return JsonResponse({'html': html}, status=HTTPStatus.BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        form_name = request.POST.get('form')
        form_class = self.form_map.get(form_name)

        if not form_class:
            raise Http404

        form = self.build_form(form_class)

        if form.is_valid():
            return self.form_valid(form_name, form)

        return self.form_invalid(form)

    def get(self, request, *args, **kwargs):
        html = render_to_string(self.template_name, {**self.get_forms()}, request=request)
        return JsonResponse(data={'html': html}, status=HTTPStatus.OK)


