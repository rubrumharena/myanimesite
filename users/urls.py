from django.urls import path

from users.views import (AccountSettingsView, CommunityListView,
                         FollowerListView, FollowingListView, HistoryListView,
                         ProfileSettingsView, ProfileView, SettingsView,
                         delete_avatar, delete_history_record, toggle_follow,
                         toggle_history_visibility, toggle_record_completion)

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
    path('ajax/toggle_record_completion/<int:record_id>/', toggle_record_completion, name='toggle_completion'),
    path('ajax/delete_history_record/<int:record_id>/', delete_history_record, name='delete_history'),
    path('ajax/toggle_history_visibility/', toggle_history_visibility, name='toggle_history_visibility'),
]
