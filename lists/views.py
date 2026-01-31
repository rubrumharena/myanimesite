from functools import cached_property
from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.aggregates import ArrayAgg
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, reverse
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic.edit import DeleteView

from common.utils.enums import FolderMethod, ListQueryParam
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
    UPDATE_FORM = 'update_folder_form'
    template_name = 'lists/folder.html'

    @cached_property
    def folder(self):
        return get_object_or_404(Folder, id=self.kwargs.get('folder_id'))

    def post(self, request, *args, **kwargs):
        if request.POST.get('form') != self.UPDATE_FORM:
            return HttpResponseRedirect(request.path_info)

        if self.folder.user != request.user:
            raise Http404

        form = FolderForm(
            data=request.POST, files=request.FILES, instance=self.folder, request=request, prefix='update'
        )

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.path_info)
        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data(**{self.UPDATE_FORM: form}))

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

        if self.folder.user == self.request.user and self.folder.name != Folder.FAVORITES:
            context[self.UPDATE_FORM] = kwargs.get(self.UPDATE_FORM, FolderForm(instance=self.folder, prefix='update'))

        return {**context, 'page_title': page_title, 'folder': self.folder}


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


@require_POST
@login_required_ajax
def update_folder_titles_ajax(request):
    try:
        folder_id = int(request.POST.get('folder_id'))
        title_id = int(request.POST.get('title_id'))
    except (ValueError, TypeError):
        return JsonResponse(data={}, status=HTTPStatus.BAD_REQUEST)
    get_object_or_404(Folder, id=folder_id, user=request.user)
    get_object_or_404(Title, id=title_id)

    method = request.POST.get('method')
    link_model = Folder.titles.through
    if method == FolderMethod.DELETE.value:
        link_model.objects.filter(folder_id=folder_id, title_id=title_id).delete()
    elif method == FolderMethod.ADD.value:
        link_model.objects.get_or_create(folder_id=folder_id, title_id=title_id)
    else:
        return JsonResponse(data={}, status=HTTPStatus.BAD_REQUEST)

    return JsonResponse(data={}, status=HTTPStatus.OK)


@require_POST
@login_required_ajax
def save_folder_ajax(request):
    form = FolderForm(data=request.POST, files=request.FILES, request=request)
    if form.is_valid():
        form.save()
        return JsonResponse(data={}, status=HTTPStatus.OK)

    return JsonResponse(data={'errors': form.errors}, status=HTTPStatus.BAD_REQUEST)


@login_required_ajax
def get_user_folders_ajax(request):
    data = {'items': []}
    folders = (
        Folder.objects.filter(user=request.user)
        .annotate(title_ids=ArrayAgg('titles__id', distinct=True))
        .only('id', 'name')
        .order_by('-updated_at')
    )
    data['items'] = [
        {'id': folder.id, 'name': folder.name, 'folder_titles': folder.title_ids if all(folder.title_ids) else []}
        for folder in folders
    ]
    return JsonResponse(data=data, status=HTTPStatus.OK)


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


def get_user_titles_ajax(request):
    user = request.user
    data = {
        'items': list(
            Folder.titles.through.objects.filter(folder__user=user).values_list('title_id', flat=True).distinct()
        )
        if user.is_authenticated
        else []
    }
    return JsonResponse(data=data, status=HTTPStatus.OK)
