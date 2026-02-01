from enum import Enum


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
