class BaseCacheKey:
    VERSION = None
    DOMAIN = None

    @classmethod
    def _build(cls, *args):
        return ':'.join([cls.VERSION, cls.DOMAIN, *map(str, args)])


class TitlesCacheKey(BaseCacheKey):
    VERSION = 'v1'
    DOMAIN = 'titles'

    @classmethod
    def title(cls, title_id: int) -> str:
        return cls._build('title', title_id)

    @classmethod
    def related_titles(cls, title_id: int) -> str:
        return cls._build('related_titles', title_id)

    @classmethod
    def title_group(cls, title_id: int) -> str:
        return cls._build('title_group', title_id)

    @classmethod
    def chart(cls, chart: str) -> str:
        return cls._build('chart', chart)


class ListsCacheKey(BaseCacheKey):
    VERSION = 'v1'
    DOMAIN = 'lists'

    def __init__(self, url: str = None, user_id: int = None, list_id: str | int = None):
        self.url = url
        self.user_id = user_id
        self.list_id = list_id

    def best_titles(self) -> str:
        return self._build(*self._gather_args('best_titles'))

    def title_count(self) -> str:
        return self._build(*self._gather_args('title_count'))

    def object_list(self) -> str:
        return self._build(*self._gather_args('object_list'))

    def resolved_path_params(self) -> str:
        return self._build(*self._gather_args('resolved_path_params'))

    def _gather_args(self, key: str) -> list:
        args = ['url', self.url, key]
        if self.user_id:
            args += ['visitor', self.user_id]
        if self.list_id:
            args.append(self.list_id)
        return args

    @classmethod
    def collection(cls, slug: str) -> str:
        return cls._build('collection', slug)

    @classmethod
    def genres(cls):
        return cls._build('genres')


class UsersCacheKey(BaseCacheKey):
    VERSION = 'v1'
    DOMAIN = 'users'

    @classmethod
    def profile_folders(cls, profile_id: int, visitor_id: int) -> str:
        return cls._build('folders', 'profile', profile_id, 'visitor', visitor_id)

    @classmethod
    def history(cls, user_id: int) -> str:
        return cls._build('history', 'user', user_id)

    @classmethod
    def recently_watched(cls, profile_id: int, visitor_id: int) -> str:
        return cls._build('history', 'profile', profile_id, 'visitor', visitor_id)
