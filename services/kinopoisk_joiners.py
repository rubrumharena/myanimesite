import itertools
from collections import defaultdict
from itertools import chain
from typing import Any

from unidecode import unidecode

from lists.models import Collection
from services.kinopoisk_api import KinopoiskClient
from titles.models import Backdrop, Group, Person, Studio, Title


def join_backdrops(title_ids: list[int]) -> None:
    step = 250
    rels = []
    instance = KinopoiskClient()
    titles = Title.objects.in_bulk(title_ids, field_name='kinopoisk_id')

    for i in range(0, len(title_ids) + 1, step):
        for title_id, backdrops in instance.get_multiple_backdrops(title_ids[i : i + step]).items():
            for backdrop in backdrops:
                rels.append(Backdrop(title=titles[title_id], backdrop_url=backdrop))
    if rels:
        Backdrop.objects.bulk_create(rels, ignore_conflicts=True)


def join_sequels_and_prequels(groups: dict[int, list[int]]) -> None:
    if any(groups.values()):
        graph = defaultdict(set, {title_id: set() for title_id in set(chain.from_iterable(groups.values()))})
        for key, value in groups.items():
            graph[key].update(value)

        # It is a dirty fix, because we change the content of the iter. object in the loop,
        # but I can't create anything better than this algorithm (maybe will change in the future),
        # and my tests say that everything still works though. STILL.

        changed = True
        while changed:
            changed = False
            for parent_id, group in graph.items():
                for child_id in group:
                    before = len(graph[child_id])
                    extra = {parent_id} if child_id != parent_id else set()
                    graph[child_id].update(set(group) - {child_id} | extra)
                    if len(graph[child_id]) > before:
                        changed = True

        objects_to_join = Title.objects.in_bulk(graph.keys(), field_name='kinopoisk_id')
        rels = []
        for parent, children in graph.items():
            parent_obj = objects_to_join.get(parent)
            if parent_obj is None:
                continue
            for child in children:
                child_obj = objects_to_join.get(child)
                if child_obj is None:
                    continue
                rels.append(Group(parent=parent_obj, child=child_obj))
        if rels:
            Group.objects.bulk_create(rels, ignore_conflicts=True)


def join_studios(data: dict[int, list[str]]) -> None:
    if any(data.values()):
        titles = Title.objects.in_bulk(data.keys(), field_name='kinopoisk_id')
        incoming_studios = set(chain.from_iterable(data.values()))

        Studio.objects.bulk_create((Studio(name=name) for name in incoming_studios), ignore_conflicts=True)
        studio_objs = {studio.name: studio for studio in Studio.objects.filter(name__in=incoming_studios)}

        rels = []
        related_model = Title.studios.through
        for title_id, studios in data.items():
            title = titles.get(title_id)
            for name in studios:
                studio = studio_objs.get(name)
                if studio and title:
                    rels.append(related_model(title=title, studio=studio))
        if rels:
            related_model.objects.bulk_create(rels, ignore_conflicts=True)


def join_persons(data: dict[int, list[dict[str, Any]]]) -> None:
    if any(data.values()):
        titles = Title.objects.in_bulk(data.keys(), field_name='kinopoisk_id')

        bulk_batch_size = 1_000
        person_map = {}
        for persons in data.values():
            for person in persons:
                person_map[person['id']] = person
        incoming_persons = person_map.values()

        persons_to_create = {
            person['id']: Person(
                kinopoisk_id=person['id'],
                name=person['name'],
                description=person.get('description'),
                profession=person['enProfession'],
                image=person['photo'],
            )
            for person in incoming_persons
        }
        Person.objects.bulk_create(persons_to_create.values(), ignore_conflicts=True, batch_size=bulk_batch_size)

        batch_size = 5_000
        person_objs = {}
        for i in range(0, len(persons_to_create), batch_size):
            batch = itertools.islice(persons_to_create.keys(), i + batch_size)
            person_objs.update(
                {person.kinopoisk_id: person for person in Person.objects.filter(kinopoisk_id__in=batch)}
            )

        rels = []
        related_model = Title.persons.through
        for title_id, persons in data.items():
            title = titles.get(title_id)
            for person in persons:
                person_obj = person_objs.get(person['id'])
                if person_obj and title:
                    rels.append(related_model(title=title, person=person_obj))
        if rels:
            related_model.objects.bulk_create(rels, ignore_conflicts=True, batch_size=bulk_batch_size)


def enrich_genres(data: dict[int, list[str]]) -> None:
    client = KinopoiskClient()
    title_ids = data.keys()
    keywords = client.get_multiple_keywords(title_ids)

    for title_id, genres in keywords.items():
        data[title_id].extend(genres)


def join_genres(data: dict[int, list[str]]) -> None:
    enrich_genres(data)

    if any(data.values()):
        titles = Title.objects.in_bulk(data.keys(), field_name='kinopoisk_id')
        incoming_genres = set(chain.from_iterable(data.values()))

        existing_genres = Collection.objects.filter(name__in=incoming_genres, type=Collection.GENRE)
        missing_genres = incoming_genres - set(existing_genres.values_list('name', flat=True))

        if missing_genres:
            genres_to_create = (
                Collection(
                    name=name, type=Collection.GENRE, slug=unidecode(name).translate(name).replace(' ', '_').lower()
                )
                for name in missing_genres
            )
            Collection.objects.bulk_create(genres_to_create)
            set(existing_genres).update(set(genres_to_create))
        genre_objs = {genre.name: genre for genre in existing_genres}

        rels = []
        related_model = Collection.titles.through
        for title_id, genres in data.items():
            title = titles.get(title_id)
            for name in genres:
                genre = genre_objs.get(name)
                if genre and title:
                    rels.append(related_model(title=title, collection=genre))
        if rels:
            related_model.objects.bulk_create(rels, ignore_conflicts=True)
