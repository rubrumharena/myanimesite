from django.urls import path

from comments.views import (CommentListView, PreviewTemplateView,
                            ReviewFormView, delete_comment, delete_review,
                            like_comment)

app_name = 'comments'

urlpatterns = [
    path('ajax/<int:title_id>/gather/', CommentListView.as_view(), name='comments'),
    path('ajax/<int:title_id>/publicate/', CommentListView.as_view(), name='publicate_comment'),
    path('ajax/like/<int:comment_id>/', like_comment, name='like_comment'),
    path('ajax/delete_comment/<int:comment_id>/', delete_comment, name='delete_comment'),
    path('delete_review/<int:title_id>/', delete_review, name='delete_review'),
    path('ajax/review/view/<int:user_id>/<int:title_id>/', PreviewTemplateView.as_view(), name='review_view'),
    path('ajax/review/edit/<int:title_id>/', ReviewFormView.as_view(), name='review_edit'),
]
