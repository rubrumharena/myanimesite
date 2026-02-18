import itertools
from collections import defaultdict
from itertools import chain

from django.conf import settings
from unidecode import unidecode

from lists.models import Collection
from services.kinopoisk_api import KinopoiskClient, TitleWrapper
from titles.models import Backdrop, Group, Person, Poster, SeasonsInfo, Statistic, Studio, Title


def data_initialization(configuration):
    instance = KinopoiskClient()
    seqs_and_preqs_permission = configuration['sequels']
    titles = instance.get_multiple_info(
        limit=configuration['limit'],
        page=configuration['page'],
        rating=configuration['rating'],
        is_series=configuration['is_series'],
        year=configuration['year'],
        genre=configuration['genre'],
    )

    incoming_data = set(TitleWrapper(title) for title in titles)

    seqs_and_preqs = set()
    if seqs_and_preqs_permission:
        incoming_kp_ids = set()
        for obj in incoming_data:
            incoming_kp_ids.add(obj.title_id)
            if obj.sequels_and_prequels:
                seqs_and_preqs.update(obj.sequels_and_prequels)
    else:
        incoming_kp_ids = set(obj.title_id for obj in incoming_data)

    existing_objs = Title.objects.filter(kinopoisk_id__in=incoming_kp_ids.union(seqs_and_preqs))
    existing_ids = set(existing_objs.values_list('kinopoisk_id', flat=True))

    nonexistent_seqs_and_preqs = (seqs_and_preqs - existing_ids) - incoming_kp_ids

    if seqs_and_preqs_permission and nonexistent_seqs_and_preqs:
        step = 250
        seqs_and_preq_creation_candidates = []
        for i in range(0, len(nonexistent_seqs_and_preqs) + 1, step):
            seqs_and_preq_creation_candidates += instance.get_multiple_info(
                title_ids=list(nonexistent_seqs_and_preqs)[i : i + step]
            )

        incoming_data |= set(TitleWrapper(title) for title in seqs_and_preq_creation_candidates)

    potential_creation_kp_ids = (incoming_kp_ids | nonexistent_seqs_and_preqs) - existing_ids

    return [obj for obj in incoming_data if obj.title_id in potential_creation_kp_ids], potential_creation_kp_ids


def create_movie_objs(data_to_create, title_ids):
    if data_to_create:
        instance = KinopoiskClient()
        excluded_genres = ('аниме', 'мультфильм')

        keywords = instance.get_multiple_keywords(title_ids)

        genres, studios, persons, groups = {}, {}, {}, {}
        objs, statistics, posters, episodes = {}, [], [], []
        for obj in data_to_create:
            objs[obj.title_id] = Title(
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
            cur_title = objs[obj.title_id]
            statistic = Statistic(
                kp_rating=obj.ratings['kp'],
                kp_votes=obj.votes['kp'],
                imdb_rating=obj.ratings['imdb'],
                imdb_votes=obj.votes['imdb'],
                title=objs[obj.title_id],
            )
            statistics.append(statistic)

            seasons_info = obj.seasons_info
            episodes += (
                generate_episode_objs(seasons_info, cur_title) if seasons_info else [SeasonsInfo(title=cur_title)]
            )

            if obj.poster:
                poster = cur_title.upload_poster(obj.poster)
                if poster is not None:
                    posters.append(poster)

            joined_genres = obj.categories + keywords.get(obj.title_id, [])
            genres[obj.title_id] = [name.capitalize() for name in joined_genres if name not in excluded_genres]
            studios[obj.title_id] = obj.production_companies
            persons[obj.title_id] = obj.persons
            groups[obj.title_id] = obj.sequels_and_prequels

        if any(objs.values()):
            Title.objects.bulk_create(objs.values())
            if statistics:
                Statistic.objects.bulk_create(statistics)
            if posters:
                Poster.objects.bulk_create(posters)
            if episodes:
                SeasonsInfo.objects.bulk_create(episodes)

            join_genres(created_objs=objs, data_to_join=genres)
            join_studios(created_objs=objs, data_to_join=studios)
            join_persons(created_objs=objs, data_to_join=persons)
            join_sequels_and_prequels(data_to_join=groups)
            join_backdrops(created_objs=objs, data_to_join=title_ids)

        if getattr(settings, 'DEBUG_RETURN_TEST_VARS', False):
            return genres


def generate_episode_objs(seasons_info, title_obj):
    episodes = []
    for season in seasons_info:
        for episode in range(1, season['episodesCount'] + 1):
            episodes.append(SeasonsInfo(title=title_obj, episode=episode, season=season['number']))
    return episodes


def join_backdrops(created_objs, data_to_join):
    step = 250
    rels = []
    instance = KinopoiskClient()
    data_to_join = list(data_to_join)
    for i in range(0, len(data_to_join) + 1, step):
        for title_id, backdrops in instance.get_multiple_backdrops(data_to_join[i : i + step]).items():
            for backdrop in backdrops:
                rels.append(Backdrop(title=created_objs[title_id], backdrop_url=backdrop))
    if rels:
        Backdrop.objects.bulk_create(rels, ignore_conflicts=True)


def join_sequels_and_prequels(data_to_join):
    if any(data_to_join.values()):
        graph = defaultdict(set, {id: set() for id in set(chain.from_iterable(data_to_join.values()))})
        for key, value in data_to_join.items():
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


def join_studios(created_objs, data_to_join):
    if any(data_to_join.values()):
        incoming_studios = set(chain.from_iterable(data_to_join.values()))

        Studio.objects.bulk_create((Studio(name=name) for name in incoming_studios), ignore_conflicts=True)
        studio_objs = {studio.name: studio for studio in Studio.objects.filter(name__in=incoming_studios)}

        rels = []
        related_model = Title.studios.through
        for title_id, studios in data_to_join.items():
            title = created_objs.get(title_id)
            for name in studios:
                studio = studio_objs.get(name)
                if studio and title:
                    rels.append(related_model(title=title, studio=studio))
        if rels:
            related_model.objects.bulk_create(rels, ignore_conflicts=True)


def join_persons(created_objs, data_to_join):
    if any(data_to_join.values()):
        bulk_batch_size = 1_000
        person_map = {}
        for persons in data_to_join.values():
            for person in persons:
                person_map[person['id']] = person
        incoming_persons = person_map.values()

        persons_to_create = {
            person['id']: Person(
                kinopoisk_id=person['id'],
                name=person['name'],
                description=person['description'],
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
        for title_id, persons in data_to_join.items():
            title = created_objs.get(title_id)
            for person in persons:
                person_obj = person_objs.get(person['id'])
                if person_obj and title:
                    rels.append(related_model(title=title, person=person_obj))
        if rels:
            related_model.objects.bulk_create(rels, ignore_conflicts=True, batch_size=bulk_batch_size)


def join_genres(created_objs, data_to_join):
    if any(data_to_join.values()):
        incoming_genres = set(chain.from_iterable(data_to_join.values()))

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
        for title_id, genres in data_to_join.items():
            title = created_objs.get(title_id)
            for name in genres:
                genre = genre_objs.get(name)
                if genre and title:
                    rels.append(related_model(title=title, collection=genre))
        if rels:
            related_model.objects.bulk_create(rels, ignore_conflicts=True)


# def join_sequels_and_prequels(created_objs, data_to_join):
#     if any(data_to_join.values()):
#         graph = defaultdict(set, {id: set() for id in set(chain.from_iterable(data_to_join.values()))})
#         for key, value in data_to_join.items():
#             graph[key].update(value)
#         # graph = defaultdict(set, {k: set(v) for k, v in data_to_join.items()})
#
#         # It is a dirty fix, because we change the content of the iter. object in the loop,
#         # but I can't create anything better than this algorithm (maybe will change in the future),
#         # and my tests say that everything still works though. STILL.
#
#
#         changed = True
#         while changed:
#             changed = False
#             for parent_id, group in graph.items():
#                 for child_id in group:
#                     # if child_id in data_to_join:
#
#                     before = len(graph[child_id])
#                     extra = {parent_id} if child_id != parent_id else set()
#                     graph[child_id].update(set(group) - {child_id} | extra)
#                     if len(graph[child_id]) > before: changed = True
#
#         print(graph)
#         library = set(Title.objects.filter(kinopoisk_id__in=graph.keys()).values_list('kinopoisk_id', flat=True))
#         rels = []
#         for parent, children in graph.items():
#             for child in children:
#                 if child in library:
#                     rels.append(Group(parent=created_objs[parent], child=created_objs[child]))
#         if rels:
#             Group.objects.bulk_create(rels, ignore_conflicts=True, unique_fields=['parent', 'child'])
