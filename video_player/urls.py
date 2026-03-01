from django.urls import path

from video_player.views import VideoPlayerView

app_name = 'video_player'

urlpatterns = [
    path(
        'ajax/get_content/<int:title_id>/',
        VideoPlayerView.as_view(),
        name='get_content',
    ),
    path(
        'ajax/save_progress/<int:title_id>/',
        VideoPlayerView.as_view(),
        name='save_progress',
    ),
]
