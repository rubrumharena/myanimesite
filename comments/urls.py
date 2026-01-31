from django.urls import path

from comments.views import CommentAjaxView, like_comment_ajax

app_name = 'comments'

urlpatterns = [
    path('ajax/comment_get/<int:title_id>/', CommentAjaxView.as_view(), name='comment_get_ajax'),
    path('ajax/comment_post/', CommentAjaxView.as_view(), name='comment_post_ajax'),
    path('ajax/like_comment_ajax/', like_comment_ajax, name='like_comment_ajax'),
]
