from django.contrib import admin

from comments.models import Comment, CommentLikeHistory

# Register your models here.

admin.site.register(Comment)
admin.site.register(CommentLikeHistory)
