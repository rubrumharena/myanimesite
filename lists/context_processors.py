from lists.models import Collection


def collection_types(request):
    return {
        'collections': {
            'genre': Collection.GENRE,
            'movie': Collection.MOVIE_COLLECTION,
            'series': Collection.SERIES_COLLECTION,
            'year': Collection.YEAR,
        }
    }
