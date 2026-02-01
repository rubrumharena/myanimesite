import imghdr
import os
import tempfile
from http import HTTPStatus
from io import BytesIO
from tempfile import NamedTemporaryFile

import requests
from deep_translator import GoogleTranslator
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import models, transaction
from PIL import Image

from common.models.querysets import TitleQuerySet
from lists.models import Collection
from services.kinopoisk_api import KinopoiskClient

# Create your models here.


class Title(models.Model):
    _MODEL_FIELDS = (
        'name',
        'alternative_name',
        'status',
        'overview',
        'age_rating',
        'tagline',
        'premiere',
        'year',
        'names',
        'imdb_id',
        'tmdb_id',
    )
    _KINOPOISK_DOMAIN = 'https://www.kinopoisk.ru'
    _IMDB_DOMAIN = 'http://www.imdb.com'

    SERIES = 'SER'
    MOVIE = 'MOV'
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

    studios = models.ManyToManyField('Studio', related_name='studios', blank=True)
    persons = models.ManyToManyField(
        'Person',
        related_name='persons',
        blank=True,
    )
    collections = models.ManyToManyField('lists.Collection', related_name='collections', blank=True)

    objects = TitleQuerySet.as_manager()

    def __str__(self):
        return f'{self.name} | {self.type} | {self.kinopoisk_id}'

    @property
    def external_urls(self):
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

    def clean(self):
        errors = {}
        if not (self.name or self.kinopoisk_id):
            errors['name'] = 'Name is required!'
        if not (self.type or self.kinopoisk_id):
            errors['type'] = 'Type is required!'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.kinopoisk_id:
            new_info = KinopoiskClient(self.kinopoisk_id)

            self._pre_save(new_info)
            super().save(*args, **kwargs)
            self._post_save(new_info)
        else:
            super().save(*args, **kwargs)

    def _pre_save(self, new_info):
        prev_info = Title.objects.filter(kinopoisk_id=self.kinopoisk_id).first() or self
        for attribute in self._MODEL_FIELDS:
            current_filling = getattr(prev_info, attribute)

            if not current_filling:
                setattr(self, attribute, getattr(new_info, attribute))

        if new_info.is_series is not None:
            if not prev_info.type:
                self.type = self.SERIES if new_info.is_series else self.MOVIE

            if not prev_info.duration:
                self.duration = new_info.series_length if new_info.is_series else new_info.movie_length

        if getattr(settings, 'DEBUG_RETURN_TEST_VARS', False):
            return self

    def _post_save(self, info):
        from services.kinopoisk_import import (generate_episode_objs,
                                               join_sequels_and_prequels)

        if info.sequels_and_prequels:
            title_id = info.title_id
            join_sequels_and_prequels({title_id: info.sequels_and_prequels})

        seasons_info = info.seasons_info

        if seasons_info:
            SeasonsInfo.objects.bulk_create(generate_episode_objs(seasons_info, self))
        else:
            SeasonsInfo.objects.create(title=self)

        Statistic.objects.update_or_create(
            title=self,
            defaults={
                'kp_rating': info.ratings.get('kp'),
                'kp_votes': info.votes.get('kp'),
                'imdb_rating': info.ratings.get('imdb'),
                'imdb_votes': info.votes.get('imdb'),
            },
        )
        self._attach_assets(info)

        transaction.on_commit(lambda: self._link_related_entities(info))

    def _attach_assets(self, info):
        try:
            self.poster
        except Title.poster.RelatedObjectDoesNotExist:
            if info.poster:
                self.upload_poster(info.poster).save()

        if Backdrop.objects.filter(title=self, backdrop_url__isnull=False).count() < 5:
            backdrops = (Backdrop(title=self, backdrop_url=backdrop) for backdrop in info.backdrops)
            if backdrops:
                Backdrop.objects.bulk_create(backdrops, ignore_conflicts=True)

    @transaction.atomic
    def _link_related_entities(self, info):
        persons = info.persons
        if persons:
            link_model = Title.persons.through
            incoming_persons = {
                person['id']: Person(
                    kinopoisk_id=person['id'],
                    name=person['name'],
                    description=person['description'],
                    profession=person['enProfession'],
                    image=person['photo'],
                )
                for person in persons
            }
            Person.objects.bulk_create(incoming_persons.values(), ignore_conflicts=True)

            existing_persons = Person.objects.filter(kinopoisk_id__in=incoming_persons)
            link_model.objects.bulk_create(
                (link_model(title=self, person=person) for person in existing_persons), ignore_conflicts=True
            )
        studios = info.production_companies
        if studios:
            link_model = Title.studios.through
            incoming_studios = [Studio(name=studio) for studio in studios]
            Studio.objects.bulk_create(incoming_studios, ignore_conflicts=True)
            existing_studios = Studio.objects.filter(name__in=incoming_studios)
            link_model.objects.bulk_create(
                (link_model(title=self, studio=studio) for studio in existing_studios), ignore_conflicts=True
            )
        genres = info.categories
        if genres:
            link_model = Title.collections.through
            excluded_genres = ('аниме', 'мультфильм')
            keywords = info.keywords
            incoming_genres = set(name.capitalize() for name in genres + keywords if name not in excluded_genres)

            existing_objs = Collection.objects.filter(name__in=incoming_genres)
            new_genres = incoming_genres - set(existing_objs.values_list('name', flat=True))
            existing_objs = set(existing_objs)
            if new_genres:
                translator = GoogleTranslator(source='ru')
                Collection.objects.bulk_create(
                    (
                        Collection(
                            name=genre,
                            type=Collection.GENRE,
                            slug=translator.translate(genre).replace(' ', '_').lower(),
                        )
                        for genre in new_genres
                    )
                )
                created_genres = Collection.objects.filter(name__in=new_genres, type=Collection.GENRE)
                existing_objs.update(created_genres)

            link_model.objects.bulk_create(
                (link_model(title=self, collection=genre) for genre in existing_objs), ignore_conflicts=True
            )

    def upload_poster(self, poster):
        allowed_extensions = ('jpeg', 'jpg', 'png', 'webp', 'tiff')
        max_image_size_kb = 5_000
        min_width = 220
        min_height = 300
        poster_dir = settings.MEDIA_ROOT / 'posters'
        if not os.path.exists(poster_dir):
            os.makedirs(poster_dir)

        response = requests.get(poster)
        if response.status_code != HTTPStatus.OK:
            print('a')
            return None

        response_content = response.content
        image_type = imghdr.what(None, h=response_content)
        if image_type.lower() not in allowed_extensions:
            print('b')
            return None

        if len(response_content) / 1_024 > max_image_size_kb:
            print('c')
            return None

        jpg_format = 'JPEG'
        poster_obj = Poster(title=self)
        tempfile.tempdir = settings.TEMP_DIR
        with NamedTemporaryFile(mode='wb+', suffix=jpg_format) as temp_file:
            temp_file.write(response_content)
            resolutions = {
                'medium': {'width': 264, 'height': 352, 'instance': poster_obj.medium},
                'small': {'width': 40, 'height': 40, 'instance': poster_obj.small},
            }

            poster_obj.original.save(f'{self.name.replace(" ", "_")}.{jpg_format}', File(temp_file), save=False)

            original = Image.open(temp_file)
            if original.width < min_width or original.height < min_height:
                print('d')
                return None

            for resolution in resolutions.values():
                buffer = BytesIO()
                resized = original.resize((resolution['width'], resolution['height']))

                try:
                    resized.save(buffer, format=jpg_format, quality=85)
                except OSError:
                    buffer.seek(0)
                    buffer.truncate(0)
                    rgb_image = resized.convert('RGB')
                    rgb_image.save(buffer, format=jpg_format, quality=85)

                    if getattr(settings, 'DEBUG_RETURN_TEST_VARS', False):
                        return True

                file_name = f'{self.name.replace(" ", "_")}_{resolution["width"]}x{resolution["height"]}.{jpg_format}'
                resolution['instance'].save(file_name, ContentFile(buffer.getvalue()), save=False)
        return poster_obj

    @property
    def media_files(self):
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
    title = models.OneToOneField('Title', on_delete=models.CASCADE, related_name='poster')
    original = models.ImageField(upload_to='posters', null=True, blank=True)
    medium = models.ImageField(upload_to='posters', null=True, blank=True)
    small = models.ImageField(upload_to='posters', null=True, blank=True)

    @property
    def media_files(self):
        return [file for file in [self.original, self.medium, self.small] if file]

    def __str__(self):
        return f'{self.title.name}'


class TitleCreationHistory(models.Model):
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
