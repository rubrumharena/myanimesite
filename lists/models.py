from django.db import models
from django.shortcuts import reverse
from unidecode import unidecode

from common.models.bases import BaseListModel
from common.utils.ui import generate_gradient


class Collection(BaseListModel):
    SERIES_COLLECTION = 'SER_COL'
    MOVIE_COLLECTION = 'MOV_COL'
    GENRE = 'GEN'
    YEAR = 'YEAR'

    TYPE_CHOICES = (
        (SERIES_COLLECTION, 'Сериалы'),
        (MOVIE_COLLECTION, 'Фильмы'),
        (GENRE, 'Жанры'),
    )

    TYPES = [
        {'title': 'Жанры', 'slug': GENRE},
        {'title': 'Сериалы', 'slug': SERIES_COLLECTION},
        {'title': 'Фильмы', 'slug': MOVIE_COLLECTION},
        {'title': 'Годы', 'slug': YEAR},
    ]

    slug = models.SlugField(max_length=40, unique=True, null=True, blank=True)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)

    def save(self, *args, **kwargs):
        self.slug = None if self.slug == '' else self.slug
        if not self.slug:
            self.slug = unidecode(self.slug).replace(' ', '_').lower()

        super().save(*args, **kwargs)

    @property
    def url(self) -> str:
        url = reverse('lists:collection')

        if self.type == self.GENRE:
            url += f'genre--{self.slug}/'
        elif self.type in (self.MOVIE_COLLECTION, self.SERIES_COLLECTION):
            url += f'{self.slug}/'

        return url

    def __str__(self):
        return self.name


class Folder(BaseListModel):
    SYSTEM_MAP = {
        'Избранное': 'titles/icons/heart.html',
    }

    SYSTEM = 'sys'
    DEFAULT = 'def'
    TYPE_CHOICES = ((SYSTEM, 'Системная'), (DEFAULT, 'Обычная'))

    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    cover = models.TextField(blank=True, null=True)
    is_hidden = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, default=DEFAULT)

    def __str__(self):
        return f'{self.name} - {self.user.username}'

    @property
    def icon(self) -> str | None:
        if self.type == self.SYSTEM:
            path = self.SYSTEM_MAP.get(self.name)
            if path:
                return path

        return None

    def save(self, *args, **kwargs):
        if not self.cover:
            self.cover = generate_gradient()
        super().save(*args, **kwargs)
