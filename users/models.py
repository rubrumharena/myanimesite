import os
import uuid
from datetime import timedelta

from django.shortcuts import reverse
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.db import models
from django.conf import settings
from django.utils.timezone import now

from accounts.models import EmailVerification
from common.utils.files import resize_image
from titles.models import Title
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
    folders = models.ManyToManyField('lists.Folder', related_name='folders', blank=True)
    is_verified = models.BooleanField(default=False)

    first_name = None
    last_name = None

    def count_folders(self):
        return Folder.objects.filter(is_hidden=False, user=self).count()

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

        resize_image(new=self.avatar, old=old_avatar, resolution=(self.AVATAR_WIDTH, self.AVATAR_HEIGHT))
        Folder.objects.get_or_create(name=Folder.FAVORITES, user=self, is_hidden=True,
                                     cover='background: radial-gradient(ellipse at bottom right, #ea3ad9 0%, #c92be7 25%, #6b2be7 50%, #3b82f6 75%, #00d4ff 100%);')
        return self

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE)
    expiration_date = models.DateTimeField()


class Follow(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey('User', on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

