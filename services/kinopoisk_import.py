from typing import Any

from django.db import transaction

from common.utils.types import KinopoiskList
from services.kinopoisk_api import KinopoiskClient, KinopoiskData
from services.kinopoisk_joiners import join_persons, join_sequels_and_prequels, join_studios
from services.tasks import enrich_titles_from_api, index_titles, load_posters
from services.utils import generate_episode_structure
from titles.models import SeasonsInfo, Statistic, Title


def create_from_filters(configuration: dict[str, Any]) -> None:
    client = KinopoiskClient()

    is_sequels = configuration['sequels']
    titles = client.get_multiple_info(
        limit=configuration['limit'],
        page=configuration['page'],
        rating=configuration['rating'],
        is_series=configuration['is_series'],
        year=configuration['year'],
        genre=configuration['genre'],
    )

    create_movie_objs(prepare_creation_candidates(titles, is_sequels))


def create_from_title_ids(title_ids: list[int]) -> None:
    client = KinopoiskClient()

    titles = client.get_multiple_info(title_ids=title_ids)

    create_movie_objs(prepare_creation_candidates(titles))


def prepare_creation_candidates(titles: KinopoiskList, is_sequels: bool = False) -> list[KinopoiskData]:
    client = KinopoiskClient()
    incoming_data = set(KinopoiskData(title) for title in titles)

    if is_sequels:
        incoming_kp_ids = set()
        for obj in incoming_data:
            incoming_kp_ids.add(obj.title_id)
            if obj.sequels_and_prequels:
                incoming_kp_ids.update(obj.sequels_and_prequels)
    else:
        incoming_kp_ids = set(obj.title_id for obj in incoming_data)

    existing_objs = Title.objects.filter(kinopoisk_id__in=incoming_kp_ids)
    existing_ids = set(existing_objs.values_list('kinopoisk_id', flat=True))

    ids_to_create = incoming_kp_ids - existing_ids

    if ids_to_create:
        step = 250
        extra_data = []
        for i in range(0, len(ids_to_create) + 1, step):
            extra_data += client.get_multiple_info(title_ids=list(ids_to_create)[i : i + step])

        incoming_data.update(set(KinopoiskData(title) for title in extra_data))

    return [obj for obj in incoming_data if obj.title_id in ids_to_create]


@transaction.atomic
def create_movie_objs(data):
    title_ids = [obj.title_id for obj in data]
    assemble_atomic(data)
    transaction.on_commit(lambda: enrich_titles_from_api.delay(title_ids))
    transaction.on_commit(lambda: index_titles.delay(title_ids))
    transaction.on_commit(lambda: batch_posters(data))


def assemble_atomic(data: list[KinopoiskData]) -> None:
    groups = {}
    titles, statistics, structure = [], [], []
    studios, persons = {}, {}
    for obj in data:
        title = Title(
            kinopoisk_id=obj.title_id,
            name=obj.name,
            alternative_name=obj.alternative_name,
            status=obj.status,
            overview=obj.overview,
            tagline=obj.tagline,
            age_rating=obj.age_rating,
            premiere=obj.premiere,
            year=obj.year,
            names=obj.names,
            imdb_id=obj.imdb_id,
            tmdb_id=obj.tmdb_id,
            type=Title.SERIES if obj.is_series else Title.MOVIE,
            duration=obj.series_length if obj.is_series else obj.movie_length,
        )

        statistic = Statistic(
            kp_rating=obj.ratings['kp'],
            kp_votes=obj.votes['kp'],
            imdb_rating=obj.ratings['imdb'],
            imdb_votes=obj.votes['imdb'],
            title=title,
        )

        seasons_info = obj.seasons_info
        if seasons_info:
            structure.extend(generate_episode_structure(seasons_info, title))
        else:
            structure.append(SeasonsInfo(title=title))

        statistics.append(statistic)
        titles.append(title)
        groups[obj.title_id] = obj.sequels_and_prequels
        studios[obj.title_id] = obj.production_companies
        persons[obj.title_id] = obj.persons

    if titles:
        Title.objects.bulk_create(titles)
        if statistics:
            Statistic.objects.bulk_create(statistics)
        if structure:
            SeasonsInfo.objects.bulk_create(structure)

        join_sequels_and_prequels(groups)
        join_studios(studios)
        join_persons(persons)


def batch_posters(data: list[KinopoiskData]) -> None:
    batch_size = 30
    posters = {obj.title_id: obj.poster for obj in data}
    keys = list(posters.keys())

    for i in range(0, len(keys), batch_size):
        cur_keys = keys[i : i + batch_size]

        batch = {k: posters[k] for k in cur_keys}
        load_posters.delay(batch)
