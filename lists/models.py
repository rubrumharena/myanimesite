from typing import Optional

from django.core.validators import FileExtensionValidator
from django.db import models
from django.shortcuts import reverse
from unidecode import unidecode

from common.models.bases import BaseListModel


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

    slug = models.SlugField(max_length=40, unique=True, null=True, blank=True)
    image = models.ImageField(
        upload_to='collections', null=True, blank=True, validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)

    def save(self, *args, **kwargs):
        self.slug = None if self.slug == '' else self.slug
        if not self.slug:
            self.slug = unidecode(self.slug).replace(' ', '_').lower()

        super().save(*args, **kwargs)

    def generate_url(self, collection_type: str, slug: Optional[str] = None) -> str:
        url = reverse('lists:collection')

        if collection_type == self.YEAR and slug is not None:
            return url + f'year--{slug}/'

        if collection_type == self.GENRE:
            url += f'genre--{self.slug}/'
        elif collection_type in (self.MOVIE_COLLECTION, self.SERIES_COLLECTION):
            url += f'{self.slug}/'

        return url

    def __str__(self):
        return self.name


class Folder(BaseListModel):
    FAVORITES = 'Избранное'

    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='folders', blank=True, null=True)
    cover = models.TextField(blank=True, null=True)
    is_hidden = models.BooleanField(default=False)
    titles = models.ManyToManyField('titles.Title', related_name='titles', blank=True)

    def __str__(self):
        return f'{self.name} - {self.user.username}'

    def save(self, *args, **kwargs):
        from common.utils.ui import generate_gradient

        if not self.cover:
            self.cover = generate_gradient()
        super().save(*args, **kwargs)
