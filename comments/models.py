from django.db import models


# Create your models here.


class Comment(models.Model):
    title = models.ForeignKey('titles.Title', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    review = models.OneToOneField(
        'titles.LibraryEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entry',
    )
    text = models.TextField()
    like_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.title.name} | {self.user.username}'


class CommentLikeHistory(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    comment = models.ForeignKey('Comment', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.comment.title.name} | {self.user.username}'
