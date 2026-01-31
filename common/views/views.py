from typing import Any, Dict

from django.db.models import Count

from common.utils.ui import generate_years_and_decades
from lists.models import Collection


def build_collection_items(collection_type: str) -> Dict[str, Any]:
    if collection_type == Collection.YEAR:
        years = generate_years_and_decades(10, True)
        return {
            'items': [
                {
                    'name': year + ' год' if '-' not in year else year[:4] + '-е',
                    'image': None,
                    'title_count': None,
                    'type': Collection.YEAR,
                    'url': Collection().generate_url(collection_type, year),
                }
                for year in years
            ]
        }

    collections = (
        Collection.objects.annotate(title_count=Count('collections'))
        .filter(type=collection_type)
        .only('name', 'image', 'type')
        .order_by('name')
    )

    return {
        'items': [
            {
                'name': item.name,
                'image': item.image.url if item.image else None,
                'title_count': item.title_count,
                'type': item.type,
                'url': item.generate_url(collection_type),
            }
            for item in collections
        ]
    }
