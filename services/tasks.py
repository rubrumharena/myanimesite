import requests
from celery import shared_task
from django.db import IntegrityError

from services.kinopoisk_api import KinopoiskClient, KinopoiskData
from services.kinopoisk_joiners import join_backdrops, join_genres
from services.utils import update_titles
from titles.documents import TitleDocument
from titles.models import Poster, Title


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def enrich_titles_from_api(title_ids: list[int]) -> None:
    client = KinopoiskClient()

    title_dicts = client.get_multiple_info(title_ids=title_ids)
    titles = list(KinopoiskData(title) for title in title_dicts)

    join_genres({obj.title_id: obj.genres for obj in titles})
    join_backdrops(title_ids)


@shared_task(autoretry_for=(requests.RequestException,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def load_posters(posters: dict) -> None:
    posters = {int(k): v for k, v in posters.items()}
    session = requests.Session()

    titles = Title.objects.in_bulk(posters.keys(), field_name='kinopoisk_id')

    for title_id, url in posters.items():
        title = titles.get(title_id)
        if not title:
            continue

        try:
            poster, _ = Poster.objects.get_or_create(title=title)
        except IntegrityError:
            poster = Poster.objects.get(title=title)

        if poster.build(url, session):
            poster.save()


@shared_task
def index_titles(title_ids: list[int]) -> None:
    if not title_ids:
        return
    titles = Title.objects.filter(kinopoisk_id__in=title_ids)
    TitleDocument().update(titles)


@shared_task
def update_actual_titles() -> None:
    titles = Title.objects.only_actual_titles()
    print(titles)
    update_titles(titles)


@shared_task
def update_all_titles() -> None:
    batch_size = 500
    titles = Title.objects.order_by('-updated_at')[:batch_size]
    update_titles(titles)
