from django.urls import path

from comments.views import CommentListView, like_comment

app_name = 'comments'

urlpatterns = [
    path('ajax/<int:title_id>/gather/', CommentListView.as_view(), name='comments'),
    path('ajax/<int:title_id>/publicate/', CommentListView.as_view(), name='publicate_comment'),
    path('ajax/like/<int:comment_id>/', like_comment, name='like_comment'),
]
