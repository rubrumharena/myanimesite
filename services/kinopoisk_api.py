import logging
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Collection

import requests

from common.utils.types import KinopoiskList
from myanimesite.settings import KINOPOISK_TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s]: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class KinopoiskClient:
    title_id: int | None = None

    EXCLUDED_GENRES = ('аниме', 'мультфильм')
    BASE_URL = 'https://api.kinopoisk.dev/v1.4/'
    HEADERS = {'accept': 'application/json', 'X-API-KEY': KINOPOISK_TOKEN}
    DEFAULT_PARAMS = {
        'sortField': 'id',
        'sortType': 1,
        'type': 'anime',
        'selectFields': [
            'id',
            'status',
            'rating',
            'genres',
            'votes',
            'sequelsAndPrequels',
            'name',
            'description',
            'premiere',
            'year',
            'slogan',
            'seasonsInfo',
            'alternativeName',
            'movieLength',
            'ageRating',
            'isSeries',
            'seriesLength',
            'poster',
            'names',
            'persons',
            'networks',
            'externalId',
        ],
    }
    KEYWORD_GENRES = (
        '29604',
        '176',
        '2336',
        '23587',
        '401',
        '21952',
        '19927',
        '15846',
        '13615',
        '1153',
        '3434',
        '85673222',
        '29217',
        '37213',
        '159',
    )

    def __hash__(self):
        return hash(self.title_id)

    def _extract_list(self, item_list: str, aim: str) -> list[Any]:
        response = self.info.get(item_list)
        if response is None or not isinstance(response, list):
            return []
        return [item.get(aim) for item in response]

    @staticmethod
    def _rename_keyword(keyword: str) -> str:
        rename_list = {'самурай': 'Самураи', 'срез жизни, повседневность': 'Повседневность', 'эротика': 'Этти'}
        return rename_list[keyword.lower()] if keyword.lower() in rename_list else keyword

    @staticmethod
    def _check_ids_length(title_ids: Collection[int]) -> None:
        titles_count = len(title_ids)
        if titles_count > 250:
            raise RuntimeError(f'Too many title_ids ({titles_count}). Max limit is 250')

    @classmethod
    def _load_json(cls, url: str) -> dict:
        try:
            response = requests.get(url, headers=cls.HEADERS)
            response.raise_for_status()
            logger.info('Successful request')
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f'Timeout when requesting to {url}')
        except requests.exceptions.HTTPError as ex:
            logger.error(f'HTTP error when requesting to {url}: {ex}')
        except requests.exceptions.RequestException as ex:
            logger.error(f'An error when requesting to {url}: {ex}')
        except (ValueError, AttributeError) as ex:
            logger.error(f'Invalid JSON from {url}: {ex}')

        return {}

    def _load_keywords(self, title_ids: Collection[int] | None = None) -> KinopoiskList:
        titles = self.title_id if title_ids is None else title_ids
        if not titles:
            logger.error(f'Failed to load keywords for {titles}')
            return []
        page = 1
        limit = 50

        query = urllib.parse.urlencode({'id': self.KEYWORD_GENRES, 'movies.id': titles}, doseq=True)

        url = f'{self.BASE_URL}keyword?page={page}&limit={limit}&selectFields=title&selectFields=movies&{query}'
        logger.info(f'Request for KEYWORDS: {url}')
        return self._load_json(url).get('docs', [])

    def _load_images(self, limit: int = 1, page: int = 1, title_ids: list[int] | None = None) -> dict:
        title_ids = self.title_id if title_ids is None else title_ids
        url = f'{self.BASE_URL}image?page={page}&limit={limit}&{urllib.parse.urlencode({"movieId": title_ids}, doseq=True)}&sortField=url&sortType=1&type=backdrops&type=wallpaper&type=screenshot'
        logger.info(f'Request for IMAGES: {url}')
        return self._load_json(url)

    @cached_property
    def info(self) -> dict[str, Any]:
        if str(self.title_id).isdigit():
            data = self._load_json(f'{self.BASE_URL}movie/{self.title_id}')

            if not data:
                logger.error(f'Failed to load title info for {self.title_id}')
                return {}
            return data

        if self.title_id:
            raise ValueError(f'Failed to load movie info for "{self.title_id}"')
        raise ValueError('Failed to load movie info. The title_id is not indicated!')

    def get_multiple_info(
        self,
        limit: int = 1,
        page: int = 1,
        rating: float | str | None = None,
        is_series: bool | None = None,
        year: int | str | None = None,
        genre: str | None = None,
        title_ids: list[int] | None = None,
    ) -> KinopoiskList:
        """
        The method expects parameters to be already validated.
        Typically, it is used only within "titles.views.bulk_title_generator_view" where parameters are always checked
        and not called elsewhere.
        Theoretically it can be implemented anywhere, but use the method carefully to avoid excess api calls.
        """

        params = {**self.DEFAULT_PARAMS, 'page': page}

        if title_ids is not None:
            self._check_ids_length(title_ids)
            limit = len(title_ids)
            params['id'] = title_ids
        else:
            filters = {
                'rating.kp': rating,
                'genres.name': genre,
                'year': year,
            }

            for param, value in filters.items():
                if value and str(value).strip():
                    params[param] = str(value).lower()

            if is_series:
                params['isSeries'] = str(is_series).lower()

        if limit:
            params['limit'] = limit

        url = self.BASE_URL + 'movie?' + urllib.parse.urlencode(params, doseq=True)
        logger.info(f'Request for INFO: {url}')

        return self._load_json(url).get('docs', [])

    def get_multiple_keywords(self, title_ids: Collection[int]) -> dict[int, list[str]]:
        self._check_ids_length(title_ids)

        keywords = self._load_keywords(title_ids=title_ids)
        if not keywords:
            return {}
        sorted_keywords = {title_id: [] for title_id in title_ids}

        title_ids = set(title_ids)
        for keyword in keywords:
            keyword_name = self._rename_keyword(keyword['title'])
            intersection = set(int(title['id']) for title in keyword['movies']) & title_ids

            for title_id in intersection:
                keyword_list = sorted_keywords[title_id]
                if keyword_name not in keyword_list:
                    keyword_list.append(keyword_name)
        return sorted_keywords

    def get_multiple_backdrops(self, title_ids: Collection[int]) -> dict[int, list[str]]:
        self._check_ids_length(title_ids)

        limit_per_page = 250
        minimal_backdrop_count = 3
        sorted_backdrops, found_this_round = defaultdict(list), defaultdict(bool)
        title_ids = set(title_ids)

        cur_page = 1
        while title_ids:
            cur_titles = title_ids.copy()
            response = self._load_images(limit=limit_per_page, page=cur_page, title_ids=list(title_ids))
            response_content = response.get('docs', [])
            if not response or response.get('total', 0) == 0:
                break

            for backdrop in response_content:
                title_id = backdrop['movieId']
                if len(sorted_backdrops[title_id]) < minimal_backdrop_count:
                    sorted_backdrops[title_id].append(backdrop['url'])
                    found_this_round[title_id] = True

            if not found_this_round or response['total'] <= limit_per_page:
                break

            title_ids = {title_id for title_id in title_ids if len(sorted_backdrops[title_id]) < minimal_backdrop_count}
            found_this_round.clear()

            if cur_titles == title_ids:
                cur_page += 1
            else:
                cur_page = 1
        return sorted_backdrops

    @cached_property
    def keywords(self) -> list:
        keywords = self._load_keywords()
        return [keyword['title'] for keyword in keywords] if keywords else []

    @cached_property
    def backdrops(self) -> list[str]:
        backdrop = self._load_images(limit=5)
        if backdrop.get('total', 0) == 0:
            return []
        return [image.get('url') for image in backdrop.get('docs')]

    @property
    def persons(self) -> KinopoiskList:
        persons = self.info.get('persons')
        cleaned_persons = []
        if not persons:
            return cleaned_persons

        for person in persons:
            if person['enProfession'] in ('director', 'actor'):
                person['name'] = person['enName'] if not person.get('name') else person['name']
                cleaned_persons.append(person)
        return cleaned_persons

    @property
    def names(self) -> list:
        names = self.info.get('names')
        cleaned_names = []
        if not names:
            return cleaned_names

        languages = ('JP', 'RU', 'UA', 'US')
        for name in names:
            lang = name.get('language')
            if not lang or lang in languages:
                cleaned_names.append(name['name'])
        return cleaned_names

    @property
    def premiere(self) -> str:
        premiere = self.info.get('premiere', {}).get('world')
        year = self.info.get('year')
        if not premiere and year:
            approx_premiere = f'{year}-01-01'
            return approx_premiere
        else:
            return premiere[:10]

    @property
    def production_companies(self) -> list:
        studios = self._extract_list('productionCompanies', 'name')
        networks = self.info.get('networks', {})

        cleaned_networks = [network['name'] for network in networks['items']] if networks else []

        return studios + cleaned_networks

    @property
    def ratings(self) -> dict:
        return self.info.get('rating', {})

    @property
    def votes(self) -> dict:
        return self.info.get('votes', {})

    @property
    def status(self) -> str | None:
        return self.info.get('status')

    @property
    def genres(self) -> list[str]:
        genres = self._extract_list('genres', 'name')
        return [name.capitalize() for name in genres if name not in self.EXCLUDED_GENRES]

    @property
    def sequels_and_prequels(self) -> list[int]:
        return self._extract_list('sequelsAndPrequels', 'id')

    @property
    def name(self) -> str:
        name = self.info.get('name')
        return name if name else self.info.get('alternativeName')

    @property
    def overview(self) -> str | None:
        return self.info.get('description')

    @property
    def year(self) -> int | None:
        return self.info.get('year')

    @property
    def tagline(self) -> str | None:
        return self.info.get('slogan')

    @property
    def alternative_name(self) -> str | None:
        return self.info.get('alternativeName')

    @property
    def movie_length(self) -> int | None:
        return self.info.get('movieLength')

    @property
    def series_length(self) -> int | None:
        return self.info.get('seriesLength')

    @property
    def age_rating(self) -> int | None:
        return self.info.get('ageRating')

    @property
    def is_series(self) -> bool:
        return self.info.get('isSeries')

    @property
    def imdb_id(self) -> str | None:
        return self.info.get('externalId', {}).get('imdb')

    @property
    def tmdb_id(self) -> int | None:
        return self.info.get('externalId', {}).get('tmdb')

    @property
    def poster(self) -> str | None:
        return self.info.get('poster', {}).get('url')

    @property
    def seasons_info(self) -> list | None:
        return self.info.get('seasonsInfo')


class KinopoiskData(KinopoiskClient):
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.title_id = data.get('id')

    @property
    def info(self) -> dict[str, Any]:
        return self.data


# t = KinopoiskClient()
#
# print(t.get_multiple_info(title_ids=[586251, 972251, 370]))
# print('\n\n\n')
# print(t.get_multiple_info(title_ids=[5190537, 5190523, 718442, 880691, 1048100]))
#
# t = KinopoiskClient(title_id=2040161)
#
# print(t.seasons_info)


# url = 'https://image.openmoviedb.com/kinopoisk-images/6201401/bebef9b9-6129-40e1-9788-86e666bf2a51/orig'
# response = requests.get(url)
#
# if response.status_code == 200:
#     with open('response.jpg', mode='wb+') as file:
#         file.write(response.content)

#
#
#
# print(KinopoiskClient().get_multiple_info(limit=1, page=1, is_series=True))
