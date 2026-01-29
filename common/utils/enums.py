import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from http import HTTPStatus
from typing import List, Optional, Any, Dict


from PIL import Image, ImageOps
from django.db.models.fields.files import ImageFieldFile
from django.http import JsonResponse
from django.utils import timezone, formats
from django.shortcuts import reverse




@dataclass
class EpisodeTracker:
    seasons: List[int] = field(default_factory=list)
    episodes: List[int] = field(default_factory=list)
    voiceovers: List[int] = field(default_factory=list)
    available_episodes: List[int] = field(default_factory=list)
    available_seasons: List[int] = field(default_factory=list)
    cur_episode: Optional[int] = None
    cur_season: Optional[int] = None
    cur_voiceover: Optional[int] = None
    time: Optional[int] = 0
    video: Optional[str] = None

class ChartType(str, Enum):
    POPULAR = 'popular'
    RATED = 'rated'
    DISCUSSED = 'discussed'

class FolderMethod(str, Enum):
    DELETE = 'delete'
    ADD = 'add'
    CREATE = 'create'
    UPDATE = 'update'

class ListSortOption(str, Enum):
    DEFAULT = 'default'
    NAME = 'name'
    PREMIERE = 'premiere'
    VOTES = 'votes'
    RATING = 'rating'

    @property
    def label(self) -> str:
        return {
            ListSortOption.DEFAULT: 'По порядку',
            ListSortOption.NAME: 'По названию',
            ListSortOption.PREMIERE: 'По дате выхода',
            ListSortOption.VOTES: 'По количеству оценок',
            ListSortOption.RATING: 'По рейтингу',
        }[self]

class ListQueryValue(Enum):
    MOVIES = 'movies'
    SERIES = 'series'
    RELEASED = 'released'
    RATED = 'rated'
    BEST = 'best'
    ANY = 'any'
    UNWATCHED = 'unwatched'

    @classmethod
    def get_f_params(cls):
        return [param for param in cls if param not in (cls.BEST, cls.ANY)]

class ListQueryParam(str, Enum):
    GENRES = 'genre'
    YEARS = 'year'
    SORT = 'sort'
    PAGE = 'page'
    FILTER = 'f'
    TAB = 'tab'