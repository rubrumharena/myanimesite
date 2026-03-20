from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models.querysets import CustomUserManager
from common.utils.files import resize_image
from common.utils.types import H, W
from lists.models import Folder

# Create your models here.


class User(AbstractUser):
    AVATAR_HEIGHT = 200
    AVATAR_WIDTH = 200
    MIN_AVATAR_WIDTH = 100
    MIN_AVATAR_HEIGHT = 100
    MAX_AVATAR_SIZE = 50

    email = models.EmailField(unique=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='users', blank=True, null=True)
    is_history_public = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    objects = CustomUserManager()

    first_name = None
    last_name = None

    def count_followers(self):
        return Follow.objects.filter(following=self).count()

    def count_followings(self):
        return Follow.objects.filter(user=self).count()

    def user_followings(self):
        return Follow.objects.filter(user=self).values_list('following', flat=True)

    def save(self, *args, **kwargs):
        self.email = None if self.email == '' else self.email
        real_user = User.objects.filter(id=self.id)
        old_avatar = real_user.first().avatar if real_user.exists() else None

        super().save(*args, **kwargs)

        resize_image(new=self.avatar, old=old_avatar, resolution=(W(self.AVATAR_WIDTH), H(self.AVATAR_HEIGHT)))

        for name in Folder.SYSTEM_MAP.keys():
            Folder.objects.get_or_create(
                name=name,
                user=self,
                is_hidden=True,
                is_pinned=True,
                type=Folder.SYSTEM,
                cover='background: radial-gradient(ellipse at bottom right, #ea3ad9 0%, #c92be7 25%, #6b2be7 50%, #3b82f6 75%, #00d4ff 100%);',
            )

        return self

    def __str__(self):
        return self.username


class Follow(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='followings')
    following = models.ForeignKey('User', on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
