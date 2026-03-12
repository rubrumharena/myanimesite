import imghdr
import os
from http import HTTPStatus
from io import BytesIO
from tempfile import NamedTemporaryFile

import requests
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from PIL import Image

from common.models.querysets import TitleQuerySet
from common.utils.ui import get_partial_fill

# Create your models here.


class Title(models.Model):
    _KINOPOISK_DOMAIN = 'https://www.kinopoisk.ru'
    _IMDB_DOMAIN = 'http://www.imdb.com'

    SERIES = 'series'
    MOVIE = 'movie'
    TYPE_CHOICES = (
        (SERIES, 'Сериал'),
        (MOVIE, 'Фильм'),
    )

    ZERO = 0
    SIX = 6
    TWELVE = 12
    SIXTEEN = 16
    EIGHTEEN = 18
    AGE_CHOICES = (
        (ZERO, '0+'),
        (TWELVE, '12+'),
        (SIXTEEN, '16+'),
        (EIGHTEEN, '18+'),
    )

    SD = 'SD'
    HD = 'HD'
    FULL_HD = 'FULL_HD'
    QUAD_HD = 'QUAD_HD'
    UHD = 'UHD'
    QUALITY_CHOICES = (
        (SD, '480p'),
        (HD, '720p'),
        (FULL_HD, '1080p'),
        (QUAD_HD, '2к'),
        (UHD, '4к'),
    )

    kinopoisk_id = models.IntegerField(null=True, blank=True, unique=True)
    imdb_id = models.CharField(max_length=10, null=True, blank=True)
    tmdb_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    names = ArrayField(models.CharField(max_length=255), null=True, blank=True)
    alternative_name = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=32, null=True, blank=True)
    overview = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, null=True, blank=True)
    age_rating = models.SmallIntegerField(null=True, blank=True, choices=AGE_CHOICES)
    duration = models.SmallIntegerField(null=True, blank=True)
    quality = models.CharField(max_length=32, null=True, blank=True, choices=QUALITY_CHOICES)
    tagline = models.CharField(max_length=255, null=True, blank=True)
    premiere = models.DateField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    studios = models.ManyToManyField('Studio', related_name='studios', blank=True)
    persons = models.ManyToManyField(
        'Person',
        related_name='persons',
        blank=True,
    )
    objects = TitleQuerySet.as_manager()

    def __str__(self):
        return f'{self.name} | {self.type} | {self.kinopoisk_id}'

    def clean(self):
        errors = {}
        if not (self.name or self.kinopoisk_id):
            errors['name'] = 'Name is required!'
        if not (self.type or self.kinopoisk_id):
            errors['type'] = 'Type is required!'

        if errors:
            raise ValidationError(errors)

    @property
    def external_urls(self) -> dict[str, str]:
        kinopoisk_type = {
            self.MOVIE: 'film',
            self.SERIES: 'series',
        }
        kinopoisk_url = (
            f'{self._KINOPOISK_DOMAIN}/{kinopoisk_type[self.type]}/{self.kinopoisk_id}/'
            if self.kinopoisk_id and self.type
            else '#'
        )
        imdb_url = f'{self._IMDB_DOMAIN}/title/{self.imdb_id}/' if self.imdb_id else '#'
        return {'kinopoisk': kinopoisk_url, 'imdb': imdb_url}

    @property
    def voiceovers(self) -> list[str]:
        from video_player.models import VideoResource

        return (
            VideoResource.objects.filter(content_unit__title=self).values_list('voiceover__name', flat=True).distinct()
        )

    @property
    def media_files(self) -> list[ImageFieldFile]:
        backdrops = [image.backdrop_local for image in self.backdrops.all() if image.backdrop_local]
        posters = self.poster.media_files
        return [*backdrops, *posters]


class Group(models.Model):
    parent = models.ForeignKey('Title', on_delete=models.CASCADE, related_name='children')
    child = models.ForeignKey('Title', on_delete=models.CASCADE, related_name='parents')

    class Meta:
        unique_together = ('parent', 'child')

    def __str__(self):
        return f'{self.parent.id} | {self.child.id}'


class Statistic(models.Model):
    title = models.OneToOneField('Title', on_delete=models.CASCADE, related_name='statistic')
    rating = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0)
    kp_rating = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0)
    imdb_rating = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0)
    votes = models.IntegerField(null=True, blank=True, default=0)
    kp_votes = models.IntegerField(null=True, blank=True, default=0)
    imdb_votes = models.IntegerField(null=True, blank=True, default=0)
    views = models.IntegerField(null=True, blank=True, default=0)

    @property
    def star_fill(self) -> dict[int, int]:
        return get_partial_fill(self.rating)

    def __str__(self):
        return f'{self.title}'


class Person(models.Model):
    ACTOR = 'actor'
    DIRECTOR = 'director'
    PROFESSION_CHOICES = (
        (ACTOR, 'Актеры'),
        (DIRECTOR, 'Режиссеры'),
    )

    kinopoisk_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    image = models.URLField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    profession = models.CharField(max_length=32, choices=PROFESSION_CHOICES)

    def __str__(self):
        return f'{self.kinopoisk_id} | {self.name}'


class Studio(models.Model):
    name = models.CharField(unique=True, max_length=255)

    def __str__(self):
        return f'{self.name}'


class Backdrop(models.Model):
    title = models.ForeignKey('Title', on_delete=models.CASCADE, related_name='backdrops')
    backdrop_url = models.URLField(null=True, blank=True)
    backdrop_local = models.ImageField(upload_to='backdrops', null=True, blank=True)

    def __str__(self):
        return f'{self.title.name}'

    class Meta:
        unique_together = ('title', 'backdrop_url')


class Poster(models.Model):
    _DIR = settings.MEDIA_ROOT / 'posters'
    _EXTENSIONS = ('jpeg', 'jpg', 'png', 'webp', 'tiff')
    _MAX_SIZE = 50_000
    _FORMAT = 'JPEG'
    _TIMEOUT = 5

    MIN_WIDTH = 220
    MIN_HEIGHT = 300

    MEDIUM_WIDTH = 264
    MEDIUM_HEIGHT = 352

    SMALL_WIDTH = 40
    SMALL_HEIGHT = 40

    title = models.OneToOneField('Title', on_delete=models.CASCADE, related_name='poster')
    original = models.ImageField(upload_to='posters', null=True, blank=True)
    medium = models.ImageField(upload_to='posters', null=True, blank=True)
    small = models.ImageField(upload_to='posters', null=True, blank=True)

    def _load_image(self, url: str, session: requests.Session) -> bytes | None:
        response = session.get(url, timeout=self._TIMEOUT)

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise requests.RequestException()

        if response.status_code >= 500:
            raise requests.RequestException()

        if response.status_code != HTTPStatus.OK:
            return None

        content = response.content
        image_type = imghdr.what(None, h=content)
        if image_type.lower() not in self._EXTENSIONS:
            return None

        if len(content) / 1_024 > self._MAX_SIZE:
            return None

        try:
            with Image.open(BytesIO(content)) as image:
                width, height = image.size

                if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
                    return None
        except Exception:
            return None

        return content

    def _create_resolutions(self, original: Image.Image) -> None:
        resolutions = {
            'medium': {'width': self.MEDIUM_WIDTH, 'height': self.MEDIUM_HEIGHT, 'instance': self.medium},
            'small': {'width': self.SMALL_WIDTH, 'height': self.SMALL_HEIGHT, 'instance': self.small},
        }

        for resolution in resolutions.values():
            buffer = BytesIO()
            resized = original.resize((resolution['width'], resolution['height']))

            try:
                resized.save(buffer, format=self._FORMAT, quality=85)
            except OSError:
                buffer.seek(0)
                buffer.truncate(0)
                rgb_image = resized.convert('RGB')
                rgb_image.save(buffer, format=self._FORMAT, quality=85)

            file_name = (
                f'{self.title.name.replace(" ", "_")}_{resolution["width"]}x{resolution["height"]}.{self._FORMAT}'
            )
            resolution['instance'].save(file_name, ContentFile(buffer.getvalue()), save=False)

    def build(self, poster_url: str, session: requests.Session) -> bool:
        os.makedirs(self._DIR, exist_ok=True)

        content = self._load_image(poster_url, session)
        if not content:
            return False

        with NamedTemporaryFile(mode='wb+', suffix=self._FORMAT, dir=settings.TEMP_DIR) as temp_file:
            temp_file.write(content)
            temp_file.seek(0)
            original = Image.open(temp_file)

            temp_file.seek(0)
            self.original.save(f'{self.title.name.replace(" ", "_")}.{self._FORMAT}', File(temp_file), save=False)
            self._create_resolutions(original)

        return True

    @property
    def media_files(self) -> list[ImageFieldFile]:
        return [file for file in [self.original, self.medium, self.small] if file]

    def __str__(self):
        return f'{self.title.name}'


class TitleImportLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    limit = models.IntegerField(null=True, blank=True, default=1)
    page = models.IntegerField(null=True, blank=True, default=1)
    rating = models.CharField(null=True, blank=True)
    is_series = models.BooleanField(null=True, blank=True)
    year = models.CharField(null=True, blank=True)
    genre = models.CharField(null=True, blank=True)
    sequels = models.BooleanField(null=True, blank=True)


class RatingHistory(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    title = models.ForeignKey('Title', on_delete=models.CASCADE)
    rating = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.id} | {self.rating}'


class SeasonsInfo(models.Model):
    title = models.ForeignKey('titles.Title', on_delete=models.CASCADE, related_name='seasons')
    episode = models.IntegerField(null=True, blank=True)
    season = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('title', 'episode', 'season')

    def __str__(self):
        return f's{self.season}e{self.episode} | {self.title.name}'
