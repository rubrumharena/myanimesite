from django.urls import path

from users.views import (AccountSettingsView, CommunityListView,
                         FollowerListView, FollowingListView, HistoryListView,
                         ProfileSettingsView, ProfileView, SettingsView,
                         check_history_ajax, delete_avatar,
                         delete_from_history_ajax, toggle_follow,
                         toggle_title_completed_ajax)

app_name = 'users'

urlpatterns = [
    path('settings/', SettingsView.as_view(), name='settings'),
    path('settings/profile', ProfileSettingsView.as_view(), name='profile_settings'),
    path('settings/account', AccountSettingsView.as_view(), name='account_settings'),
    path('delete_avatar/', delete_avatar, name='delete_avatar'),
    path('users/toggle_follow/<int:target_id>/', toggle_follow, name='toggle_follow'),
    path('profile/<str:username>/followers/', FollowerListView.as_view(), name='followers'),
    path('profile/<str:username>/followings/', FollowingListView.as_view(), name='followings'),
    path('history/', HistoryListView.as_view(), name='history'),
    path('profile/<str:username>/', ProfileView.as_view(), name='profile'),
    path('community/', CommunityListView.as_view(), name='community'),
    path('ajax/toggle_viewing_completed_ajax/', toggle_title_completed_ajax, name='toggle_viewing_completed_ajax'),
    path('ajax/delete_from_history_ajax/', delete_from_history_ajax, name='delete_from_history_ajax'),
    path('ajax/check_history_ajax/', check_history_ajax, name='check_history_ajax'),
]
