from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Count
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from elasticsearch.dsl import Q as ES_Q

from common.utils.wrappers import login_required_ajax
from common.views.bases import BaseSettingsView
from common.views.mixins import FollowMixin, PageTitleMixin, PaginatorMixin
from lists.models import Folder
from titles.models import Title
from users.documents import UserDocument
from users.forms import AvatarUpdateForm, EmailUpdateForm, HistoryVisibilityForm, PasswordUpdateForm, ProfileUpdateForm
from users.models import Follow, User
from video_player.models import ViewingHistory

# Create your views here.


class ProfileView(DetailView):
    template_name = 'users/profile.html'
    model = User
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        visitor = self.request.user
        profile_user = context['user']

        base_cache_key = f'profile:{profile_user.id}:visitor{visitor.id}'
        folders_key = f'{base_cache_key}:folders'
        recently_watched_key = f'{base_cache_key}:recently_watched'

        folders = cache.get(folders_key)
        if folders is None:
            folders = (
                Folder.objects.filter(user=profile_user)
                .annotate(
                    count=Count('titles'),
                )
                .only('name', 'image', 'cover')
                .order_by('-is_pinned', '-updated_at', '-id')
            )

            if visitor != profile_user:
                folders = folders.filter(is_hidden=False)
            cache.set(folders_key, folders, 60 * 15)

        recently_watched = cache.get(recently_watched_key)
        if recently_watched is None:
            recently_watched = []
            if visitor == profile_user or not profile_user.is_history_public:
                record_ids = list(
                    ViewingHistory.objects.filter(user=profile_user, position__gt=0)
                    .values_list('resource__content_unit__title_id', flat=True)
                    .order_by('resource__content_unit__title', '-watched_at')
                    .distinct('resource__content_unit__title')[:5]
                )
                if record_ids:
                    recently_watched = Title.objects.filter(id__in=record_ids).with_genres()
            cache.set(recently_watched_key, recently_watched, 60 * 5)

        title = f'{profile_user.name if profile_user.name else profile_user.username} (@{profile_user.username}) | MYANIMESITE'

        return {
            **context,
            'folders': folders,
            'page_title': title,
            'recently_watched': recently_watched,
        }


class FollowerListView(FollowMixin, ListView):
    model = User
    template_name = 'users/followers.html'
    page_title = 'Подписчики'

    def get_queryset(self):
        return (
            User.objects.filter(followings__following__username=self.kwargs['username'])
            .order_by('followings__created_at')
            .with_counts()
        )


class FollowingListView(FollowMixin, ListView):
    model = User
    template_name = 'users/followings.html'
    page_title = 'Подписки'

    def get_queryset(self):
        return (
            User.objects.filter(followers__user__username=self.kwargs['username'])
            .order_by('followers__created_at')
            .with_counts()
        )


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'users/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['page_title'] = (
            f'{user.name if user.name else user.username} (@{user.username}) | Настройки | MYANIMESITE'
        )

        return context


class AccountSettingsView(BaseSettingsView):
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
            messages.success(
                self.request,
                '⚠️ Мы отправили письмо с подтверждением на ваш email. Пожалуйста,'
                ' проверьте свой почтовый ящик и нажмите на ссылку для подтверждения.',
                extra_tags='email',
            )

        if form_name == 'password_form':
            messages.success(self.request, '✅ Пароль успешно изменен!', extra_tags='password')

        response = super().form_valid(form_name, form)

        if form_name == 'password_form':
            update_session_auth_hash(self.request, self.request.user)

        return response


class ProfileSettingsView(BaseSettingsView):
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

    @cached_property
    def record_ids(self) -> list[int]:
        return list(
            ViewingHistory.objects.filter(user=self.request.user, position__gt=0)
            .values_list('id', flat=True)
            .distinct('resource__content_unit__title')
        )

    def get_queryset(self):
        cache_key = f'history:user:{self.request.user.id}'
        queryset = cache.get(cache_key)
        if queryset is not None:
            return queryset

        queryset = (
            ViewingHistory.objects.filter(id__in=self.record_ids)
            .select_related(
                'resource__content_unit__title__poster', 'resource__voiceover', 'resource__content_unit__title'
            )
            .order_by('completed', '-watched_at')
        )
        cache.set(cache_key, queryset, 60 * 15)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return {**context, 'title_count': len(self.record_ids)}


class CommunityListView(PaginatorMixin, PageTitleMixin, ListView):
    model = User
    template_name = 'users/community.html'
    paginate_by = 10
    page_title = 'Сообщество | MYANIMESITE'

    def get_queryset(self):
        search_field = self.request.GET.get('search')

        if search_field:
            q = ES_Q(
                'bool',
                should=[
                    ES_Q('multi_match', query=search_field, fields=['name', 'username']),
                    ES_Q(
                        'multi_match',
                        query=search_field,
                        fields=['name', 'username'],
                        type='phrase_prefix',
                    ),
                ],
            )
            users = UserDocument.search().query(q).to_queryset()
        else:
            users = User.objects.all()

        return users.with_counts()


@login_required_ajax
@require_POST
def toggle_record_completion(request, record_id):
    record = get_object_or_404(ViewingHistory, id=record_id, user=request.user)
    record.completed = not record.completed
    record.save()
    return JsonResponse(data={}, status=HTTPStatus.OK)


@login_required_ajax
@require_POST
def delete_history_record(request, record_id):
    record = get_object_or_404(ViewingHistory, id=record_id, user=request.user)
    ViewingHistory.objects.filter(
        resource__content_unit__title=record.resource.content_unit.title, user=request.user
    ).delete()

    data = {}
    if ViewingHistory.objects.filter(user=request.user).count() == 0:
        data['redirect'] = reverse('users:profile', args=(request.user.username,))

    return JsonResponse(data=data, status=HTTPStatus.OK)


@login_required_ajax
@require_POST
def toggle_history_visibility(request):
    user = request.user
    user.is_history_public = not user.is_history_public
    user.save()
    return JsonResponse(data={'isEnabled': user.is_history_public}, status=HTTPStatus.OK)


@login_required
@require_POST
def toggle_follow(request, target_id):
    user = request.user
    if not user.is_verified:
        messages.warning(
            request,
            'Чтобы подписаться на пользователя вы обязаны верифицировать ваш аккаунт через почту!',
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
