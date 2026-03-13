from typing import TypeVar

from django.db.models import QuerySet
from django.utils import timezone
from requests import Session

from services.kinopoisk_api import KinopoiskClient, KinopoiskData
from titles.models import Poster, SeasonsInfo, Statistic, Title

T = TypeVar('T')


def generate_episode_structure(seasons_info: list[dict], title: Title) -> list[SeasonsInfo]:
    episodes = []
    for season in seasons_info:
        for episode in range(1, season['episodesCount'] + 1):
            episodes.append(SeasonsInfo(title=title, episode=episode, season=season['number']))
    return episodes


def update_statistics(titles: QuerySet[Title], data: list[KinopoiskData]) -> None:
    statistics = Statistic.objects.filter(title__in=titles).select_related('title')
    statistic_map = build_object_map(statistics)

    for obj in data:
        statistic = statistic_map.get(obj.title_id)
        if not statistic:
            continue

        statistic.kp_rating = obj.ratings['kp']
        statistic.kp_votes = obj.votes['kp']
        statistic.imdb_rating = obj.ratings['imdb']
        statistic.imdb_votes = obj.votes['imdb']

    Statistic.objects.bulk_update(statistics, ['kp_rating', 'imdb_rating', 'kp_votes', 'imdb_votes'])


def update_posters(titles: QuerySet[Title], data: list[KinopoiskData]) -> None:
    session = Session()

    posters = Poster.objects.filter(title__in=titles).select_related('title')
    poster_map = build_object_map(posters)

    for obj in data:
        if not obj.poster:
            continue
        poster = poster_map.get(obj.title_id)
        if not poster:
            try:
                title = titles.get(kinopoisk_id=obj.title_id)
                poster = Poster(title=title)
            except Title.DoesNotExist:
                continue

        if poster.build(obj.poster, session):
            poster.save()


def build_object_map(objs: QuerySet[T]) -> dict[int, T]:
    return {obj.title.kinopoisk_id: obj for obj in objs}


def update_titles(titles: QuerySet[Title]) -> None:
    if not titles:
        return

    client = KinopoiskClient()
    kp_ids = [title.kinopoisk_id for title in titles]
    data = client.get_multiple_info(title_ids=kp_ids)
    kinopoisk_data = [KinopoiskData(title) for title in data]

    update_statistics(titles, kinopoisk_data)
    update_posters(titles, kinopoisk_data)

    now = timezone.now()
    for title in titles:
        title.updated_at = now
    Title.objects.bulk_update(titles, fields=['updated_at'])
