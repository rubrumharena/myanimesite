from urllib.parse import urlencode

from django.http import QueryDict


def safe_int(value: str) -> int | None:
    try:
        result = int(value) if value not in (None, '', 'null') else None
    except TypeError:
        result = None
    return result


def exclude_params(query_params: QueryDict, to_exclude: str) -> str:
    exclude_list = to_exclude.strip().split(',')
    params = dict(query_params.lists())
    for param in exclude_list:
        params.pop(param, None)
    url = urlencode(params, doseq=True)

    return '?' + url if url else ''
