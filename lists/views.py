from functools import cached_property
from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Count, Exists, OuterRef
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, reverse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.views.generic.edit import DeleteView, FormView

from common.utils.enums import ListQueryParam
from common.utils.ui import generate_years_and_decades
from common.utils.wrappers import login_required_ajax
from common.views.bases import BaseListView
from lists.forms import FolderForm
from lists.models import Collection, Folder
from titles.models import Title


class CollectionListView(BaseListView):
    template_name = 'lists/collection.html'
    route = reverse_lazy('lists:collection')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        path_params = self.resolved_path_params
        slug = path_params['collection']['slug'] or path_params['genre']['slug']
        cache_key = f'{slug}:page_title'
        collection = cache.get(cache_key)
        if collection is None:
            collection = get_object_or_404(Collection, slug=slug)
            cache.set(cache_key, collection, 60**2 * 24)

        if path_params['collection']['slug']:
            page_title = slug
        else:
            page_title = self.generate_collection_title(
                path_params,
                self.request.GET.getlist(ListQueryParam.FILTER.value),
                collection,
            )

        return {**context, 'page_title': page_title + ' | MYANIMESITE', 'collection': collection, 'header': page_title}


class FolderListView(BaseListView):
    template_name = 'lists/folder.html'

    @property
    def is_private(self):
        return self.folder.user != self.request.user and self.folder.is_hidden

    @cached_property
    def cache_key(self):
        key = super().cache_key
        return f'folder:{self.folder.id}:watched_by:{self.request.user.username}:{key}'

    @cached_property
    def folder(self) -> Folder:
        return get_object_or_404(Folder, id=self.kwargs.get('folder_id'))

    @cached_property
    def base_queryset(self):
        if self.is_private:
            return Title.objects.none()
        return super().base_queryset.filter(folder_titles=self.folder)

    def get_context_data(self, **kwargs):
        self.route = reverse('lists:folder', kwargs={'folder_id': self.folder.id})
        context = super().get_context_data(**kwargs)

        username = self.folder.user.username

        base_title = f' пользователя {self.folder.user.name or username} (@{username}) | MYANIMESITE'
        page_title = ('Приватная папка' if self.is_private else f'Папка "{self.folder.name}"') + base_title

        is_editable = self.request.user == self.folder.user and self.folder.type == Folder.DEFAULT

        return {**context, 'page_title': page_title, 'folder': self.folder, 'is_editable': is_editable}


class FolderDeleteView(LoginRequiredMixin, DeleteView):
    model = Folder

    def get_success_url(self):
        return reverse('users:profile', kwargs={'username': self.request.user.username})

    def get_object(self, queryset=None):
        try:
            folder_id = int(self.kwargs.get('folder_id'))
        except (ValueError, TypeError):
            raise Http404

        return get_object_or_404(Folder, id=folder_id, user=self.request.user)


class FolderFormView(LoginRequiredMixin, FormView):
    template_name = 'lists/modal_windows/_folder_popup.html'
    form_class = FolderForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs['request'] = self.request
        kwargs['initial']['title'] = self.request.GET.get('title_id')

        folder_id = self.request.GET.get('folder_id')
        try:
            if folder_id:
                kwargs['instance'] = Folder.objects.filter(id=folder_id).first()
        except (ValueError, TypeError):
            ...

        return kwargs

    def get(self, request, *args, **kwargs):
        form = self.get_form()

        return JsonResponse(
            data={'html': render_to_string(self.template_name, {'form': form}, request)}, status=HTTPStatus.OK
        )

    def form_valid(self, form):
        is_update = form.instance.id is not None
        folder = form.save()

        if is_update:
            return JsonResponse(
                data={'redirect': reverse('lists:folder', kwargs={'folder_id': folder.id})}, status=HTTPStatus.OK
            )

        return JsonResponse(data={}, status=HTTPStatus.CREATED)

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)

        return JsonResponse(
            {'html': render_to_string(self.template_name, {'form': form}, request)}, status=HTTPStatus.BAD_REQUEST
        )


@method_decorator(cache_page(60**2 * 24 * 3), name='dispatch')
class GetCollectionsView(TemplateView):
    template_name = 'lists/modal_windows/_collections_popup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collection_type = self.kwargs['c_type']
        if collection_type == Collection.YEAR:
            years = generate_years_and_decades(10, True)
            collections = [
                {
                    'name': year + ' год' if '-' not in year else year[:4] + '-е',
                    'image': None,
                    'title_count': None,
                    'type': Collection.YEAR,
                    'url': reverse('lists:collection') + f'year--{year}/',
                }
                for year in years
            ]
        else:
            collections = (
                Collection.objects.annotate(title_count=Count('titles'))
                .filter(type=collection_type)
                .only('name', 'image', 'type')
                .order_by('name')
            )

        return {**context, 'collections': collections, 'types': Collection.TYPES, 'cur_type': collection_type}

    def get(self, request, *args, **kwargs):
        return JsonResponse(
            data={'html': render_to_string(self.template_name, self.get_context_data(**kwargs), request)},
            status=HTTPStatus.OK,
        )


class GetFoldersView(LoginRequiredMixin, TemplateView):
    template_name = 'lists/modal_windows/_library_popover.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        title = get_object_or_404(Title, id=self.kwargs['title_id'])

        folders = (
            Folder.objects.filter(user=self.request.user)
            .annotate(
                is_checked=Exists(
                    Folder.titles.through.objects.filter(
                        folder_id=OuterRef('id'),
                        title=title,
                    )
                )
            )
            .order_by('-type', '-is_pinned', '-updated_at', '-id')
        )
        return {**context, 'folders': folders, 'title': title}

    def get(self, request, *args, **kwargs):
        return JsonResponse(
            data={'html': render_to_string(self.template_name, self.get_context_data(**kwargs), request)},
            status=HTTPStatus.OK,
        )


@require_POST
@login_required_ajax
def toggle_folder_title(request, folder_id, title_id):
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    title = get_object_or_404(Title, id=title_id)

    if folder.titles.filter(id=title_id).exists():
        folder.titles.remove(title)
        status = HTTPStatus.OK
    else:
        folder.titles.add(title)
        status = HTTPStatus.CREATED

    return JsonResponse(
        data={'titleId': title_id, 'curCount': Folder.objects.filter(user=request.user, titles__id=title_id).count()},
        status=status,
    )
