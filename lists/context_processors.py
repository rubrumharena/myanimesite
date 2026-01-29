from common.utils.enums import FolderMethod
from lists.models import Folder, Collection


def collection_types(request):
    return {'collections':
        {
            'genre': Collection.GENRE,
            'movie': Collection.MOVIE_COLLECTION,
            'series': Collection.SERIES_COLLECTION,
            'year': Collection.YEAR
        }
    }


def folder_helper(request):
    return {
        'folder_helper': {
            'folder_methods': {method.name: method.value for method in FolderMethod},
            'reserved_folders': {'favorites': Folder.FAVORITES}
        }
    }
