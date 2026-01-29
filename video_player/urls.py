from django.urls import path

from video_player.views import VideoPlayerAjaxView

app_name = 'video_player'

urlpatterns = [
    path('ajax/get_video_content_ajax/<int:title_id>/', VideoPlayerAjaxView.as_view(), name='get_video_content_ajax'),
    path('ajax/save_watching_info_ajax/', VideoPlayerAjaxView.as_view(), name='save_watching_info_ajax'),
]