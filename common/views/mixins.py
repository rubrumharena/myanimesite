from abc import ABC

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from lists.forms import FolderForm
from users.models import User


class PageTitleMixin:
    page_title = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.page_title

        return context


class PaginatorMixin(ABC):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not issubclass(cls, ListView):
            raise TypeError(f'{cls.__name__} must inherit from ListView to use PaginatorMixin')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get('paginator')
        object_list = context.get('object_list')
        page_obj = context.get('page_obj')
        context['page_error'] = not object_list and paginator and paginator.count > 0
        if page_obj:
            context['page_range'] = paginator.get_elided_page_range(number=page_obj.number, on_each_side=2, on_ends=1)
        return context

    def paginate_queryset(self, queryset, page_size):
        try:
            return super().paginate_queryset(queryset, page_size)
        except (Http404, PageNotAnInteger, EmptyPage):
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.page(1)
            return paginator, page_obj, [], page_obj.has_other_pages()


class FolderFormMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['folder_form'] = FolderForm()

        return context


class FollowMixin:
    paginate_by = 24
    page_title = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, username=self.kwargs['username'])
        return {
            **context,
            'user': user,
            'page_title': f'{self.page_title} пользователя {user.name if user.name else user.username} (@{user.username}) | MYANIMESITE',
        }
