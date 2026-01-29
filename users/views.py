from http import HTTPStatus

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages import get_messages
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, Q, Case, When, Value, IntegerField
from django.http import HttpResponseRedirect, JsonResponse, Http404, request
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.views.generic.base import TemplateView, View
from django.views.generic.list import ListView
from django.contrib import messages
from elasticsearch.dsl import Q as ES_Q
from django.contrib.messages import constants

from common.utils.wrappers import login_required_ajax
from common.views.bases import BaseSettingsView
from common.views.mixins import PageTitleMixin, PaginatorMixin, FollowMixin, FolderFormMixin
from titles.models import Title
from users.documents import UserDocument

from users.forms import ProfileUpdateForm, PasswordUpdateForm, AvatarUpdateForm, EmailUpdateForm, HistoryVisibilityForm
from users.models import User, Follow
from lists.models import Folder, Collection
from video_player.models import ViewingHistory


# Create your views here.


class ProfileView(FolderFormMixin, DetailView):
    template_name = 'users/profile.html'
    model = User
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = self.get_object()

        folders = (
            Folder.objects
            .filter(user=profile_user)
            .annotate(
                count=Count('titles'),
                is_fav=Case(
                    When(name=Folder.FAVORITES, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                )
            )
            .only('name', 'image', 'cover')
            .order_by('is_fav', '-updated_at')
        )

        if self.request.user != profile_user:
            folders = folders.filter(is_hidden=False)

        recently_watched = []
        if self.request.user == profile_user or not profile_user.is_history_public:
            record_ids = list(ViewingHistory.objects
                              .filter(user=self.request.user, position__gt=0)
                              .select_related('resource__content_unit__title__poster')
                              .values_list('resource__content_unit__title_id', flat=True)
                              .order_by('resource__content_unit__title', '-watched_at')
                              .distinct('resource__content_unit__title'))
            if record_ids:
                recently_watched = Title.objects.annotate(genres=ArrayAgg('collections__name',
                                                                          filter=Q(collections__type=Collection.GENRE),
                                                                          distinct=True)).select_related('poster',
                                                                                                         'statistic').filter(
                    id__in=record_ids)
        title = f'{profile_user.name if profile_user.name else profile_user.username} (@{profile_user.username}) | MYANIMESITE'

        return {**context, 'folders': folders, 'page_title': title, 'recently_watched': recently_watched}


class FollowerListView(FollowMixin, ListView):
    model = User
    template_name = 'users/followers.html'
    page_title = 'Подписчики'

    def get_queryset(self):
        return User.objects.filter(following__following__username=self.kwargs['username']).order_by(
            'following__created_at')


class FollowingListView(FollowMixin, ListView):
    model = User
    template_name = 'users/followings.html'
    page_title = 'Подписки'

    def get_queryset(self):
        return User.objects.filter(followers__user__username=self.kwargs['username']).order_by('followers__created_at')


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'users/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context[
            'page_title'] = f'{user.name if user.name else user.username} (@{user.username}) | Настройки | MYANIMESITE'

        return context


class AccountSettingsView(BaseSettingsView, View):
    template_name = 'users/modules/forms/_account.html'
    form_map = {
        'password_form': PasswordUpdateForm,
        'email_form': EmailUpdateForm,
    }

    def build_form(self, form_class, data_required=True):
        data = self.request.POST if data_required else None

        if form_class is PasswordUpdateForm:
            return form_class(data=data, user=self.request.user)

        return form_class(data=data, instance=self.request.user)

    def form_valid(self, form_name, form):
        if form_name == 'email_form':
            messages.success(self.request, '⚠️ Мы отправили письмо с подтверждением на ваш email. Пожалуйста,'
                              ' проверьте свой почтовый ящик и нажмите на ссылку для подтверждения.', extra_tags='email')

        if form_name == 'password_form':
            messages.success(self.request, '✅ Пароль успешно изменен!', extra_tags='password')

        response = super().form_valid(form_name, form)

        if form_name == 'password_form':
            update_session_auth_hash(self.request, self.request.user)

        return response


class ProfileSettingsView(BaseSettingsView, View):
    template_name = 'users/modules/forms/_profile.html'
    form_map = {
        'profile_form': ProfileUpdateForm,
        'avatar_form': AvatarUpdateForm,
        'history_form': HistoryVisibilityForm,
    }

    def build_form(self, form_class, data_required=True):
        data = self.request.POST if data_required else None
        user = self.request.user
        if form_class is AvatarUpdateForm:
            return form_class(data=data, files=self.request.FILES or None, instance=user)

        return form_class(data=data, instance=user)


class HistoryListView(PageTitleMixin, PaginatorMixin, LoginRequiredMixin, ListView):
    model = ViewingHistory
    template_name = 'users/history.html'
    page_title = 'История просмотров | MYANIMESITE'
    paginate_by = 64

    def get_queryset(self):
        record_ids = (ViewingHistory.objects
                      .filter(user=self.request.user, position__gt=0)
                      .values_list('id', flat=True)
                      .order_by('resource__content_unit__title', '-watched_at')
                      .distinct('resource__content_unit__title'))

        return (ViewingHistory.objects
                .filter(id__in=record_ids)
                .select_related('resource__content_unit__title__poster', 'resource__voiceover')
                .order_by('completed', '-watched_at'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        title_count = ViewingHistory.objects.filter(user=self.request.user, position__gt=0).distinct(
            'resource__content_unit__title').count()

        return {**context, 'title_count': title_count}


class CommunityListView(PaginatorMixin, PageTitleMixin, ListView):
    model = User
    template_name = 'users/community.html'
    paginate_by = 10
    page_title = 'Сообщество | MYANIMESITE'

    def get_queryset(self):
        search_field = self.request.GET.get('search_field')

        if search_field:
            q = ES_Q('bool', should=[
                ES_Q('multi_match', query=search_field, fields=['name', 'username']),
                ES_Q('multi_match', query=search_field, fields=['name', 'username'],
                     type='phrase_prefix')
            ])
            users = UserDocument.search().query(q).to_queryset()
        else:
            users = User.objects.all()

        return users


@login_required_ajax
@require_POST
def toggle_title_completed_ajax(request):
    try:
        record_id = int(request.POST.get('record_id'))
    except (TypeError, ValueError):
        return JsonResponse(data={}, status=HTTPStatus.BAD_REQUEST)
    record = get_object_or_404(ViewingHistory, id=record_id, user=request.user)
    record.completed = True if not record.completed else False
    record.save()
    return JsonResponse(data={}, status=HTTPStatus.OK)


@login_required_ajax
@require_POST
def delete_from_history_ajax(request):
    try:
        record_id = int(request.POST.get('record_id'))
    except (TypeError, ValueError):
        return JsonResponse(data={}, status=HTTPStatus.BAD_REQUEST)

    last_record = get_object_or_404(ViewingHistory, id=record_id, user=request.user)
    title = Title.objects.get(id=last_record.resource.content_unit.title_id)
    ViewingHistory.objects.filter(user=request.user, resource__content_unit__title=title).delete()

    return JsonResponse(data={}, status=HTTPStatus.OK)


@login_required
@require_POST
def toggle_follow(request, target_id):
    user = request.user
    if not user.is_verified:
        messages.warning(
            request,
            'Чтобы подписаться на пользователя вы обязаны верифицировать ваш аккаунт через почту!'
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    if user.id == target_id:
        raise Http404
    following = get_object_or_404(User, id=target_id)
    obj, created = Follow.objects.get_or_create(user=user, following=following)

    if not created:
        obj.delete()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def delete_avatar(request):
    avatar = request.user.avatar
    if avatar:
        avatar.delete()
    return HttpResponseRedirect(reverse('users:settings'))


@login_required_ajax
@require_POST
def check_history_ajax(request):
    user = request.user
    user.is_history_public = not user.is_history_public
    user.save()
    return JsonResponse(data={'is_enabled': user.is_history_public}, status=HTTPStatus.OK)
