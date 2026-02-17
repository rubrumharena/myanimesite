from functools import cached_property
from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Exists, OuterRef
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, reverse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic.edit import DeleteView, FormView

from common.utils.enums import ListQueryParam
from common.utils.wrappers import login_required_ajax
from common.views.bases import BaseListView
from common.views.views import build_collection_items
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
        collection = get_object_or_404(Collection, slug=slug) if slug else None
        page_title = self.generate_collection_title(path_params, self.request.GET.getlist(ListQueryParam.FILTER.value))

        return {**context, 'page_title': page_title + ' | MYANIMESITE', 'collection': collection, 'header': page_title}


class FolderListView(BaseListView):
    template_name = 'lists/folder.html'

    @cached_property
    def folder(self) -> Folder:
        return get_object_or_404(Folder, id=self.kwargs.get('folder_id'))

    def get_queryset(self):
        if self.folder.is_hidden and self.folder.user != self.request.user:
            return Title.objects.none()
        return super().get_queryset().filter(titles=self.folder)

    def get_context_data(self, **kwargs):
        self.route = reverse('lists:folder', kwargs={'folder_id': self.folder.id})
        context = super().get_context_data(**kwargs)

        username = self.folder.user.username

        base_title = f'пользователя {self.folder.user.name or username} (@{username}) | MYANIMESITE'
        page_title = (
            'Приватная папка '
            if self.folder.user != self.request.user and self.folder.is_hidden
            else f'Папка "{self.folder.name}" '
        ) + base_title

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


@login_required_ajax
def get_folders(request, title_id):
    title = get_object_or_404(Title, id=title_id)

    folders = (
        Folder.objects.filter(user=request.user)
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

    return JsonResponse(
        data={
            'html': render_to_string(
                'lists/modal_windows/_library_popover.html', {'folders': folders, 'title': title}, request
            )
        },
        status=HTTPStatus.OK,
    )


def get_collections_ajax(request):
    collection_type = request.GET.get('type')

    if collection_type not in {
        Collection.GENRE,
        Collection.SERIES_COLLECTION,
        Collection.MOVIE_COLLECTION,
        Collection.YEAR,
    }:
        return JsonResponse(data={'items': []}, status=HTTPStatus.NOT_FOUND)

    return JsonResponse(data=build_collection_items(collection_type), status=HTTPStatus.OK)
