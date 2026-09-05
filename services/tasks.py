from concurrent.futures import ThreadPoolExecutor

import requests
import tmdbsimple as tmdb
from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from django.db import IntegrityError, transaction

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
    if not settings.ELASTICSEARCH_ENABLED or not title_ids:
        return
    titles = Title.objects.filter(kinopoisk_id__in=title_ids)
    TitleDocument().update(titles)


@shared_task
def update_actual_titles() -> None:
    titles = Title.objects.only_actual_titles()
    update_titles(titles)


@shared_task
def update_all_titles() -> None:
    batch_size = 500
    titles = Title.objects.order_by('-updated_at')[:batch_size]
    update_titles(titles)


def fetch_one(imdb_id: int, is_series: bool) -> dict[str, str | int]:
    if not imdb_id:
        return {}

    try:
        title = tmdb.Find(imdb_id)
    except requests.exceptions.HTTPError:
        return {}

    resp = title.info(external_source='imdb_id')
    data = resp.get('tv_results') or resp.get('movie_results')
    if not data:
        return {}

    tmdb_id = data[0]['id']
    item = tmdb.TV(tmdb_id).info() if is_series else tmdb.Movies(tmdb_id).info()

    return {
        'imdb_id': imdb_id,
        'name_en': item.get('name') or item.get('title'),
        'overview_en': item.get('overview'),
        'tagline_en': item.get('tagline'),
    }


@shared_task(
    autoretry_for=(requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError),
    retry_backoff=2,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
)
def translate_titles(pairs: list[dict[str, str]]):
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = [r for r in pool.map(lambda p: fetch_one(**p), pairs) if r]
    if not rows:
        return

    fields = ['name_en', 'overview_en', 'tagline_en']
    title_map = Title.objects.in_bulk([r['imdb_id'] for r in rows], field_name='imdb_id')

    to_update = []
    for r in rows:
        title = title_map.get(r['imdb_id'])
        if title is None:
            continue
        changed = False
        for field in fields:
            val = r.get(field)
            if val and getattr(title, field) != val:
                setattr(title, field, val)
                changed = True
        if changed:
            to_update.append(title)

    if not to_update:
        return

    with transaction.atomic():
        Title.objects.bulk_update(to_update, fields, batch_size=5_000)
        transaction.on_commit(lambda: call_command('update_translation_fields'))
