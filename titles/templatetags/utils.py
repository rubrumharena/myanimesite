import json
import random
from datetime import datetime
from typing import Any, Iterable
from urllib.parse import urlencode

from django import template
from django.http import QueryDict
from django.utils.safestring import mark_safe

from common.utils.humanizers import define_firm_ending, define_soft_ending, humanize_date_time
from titles.models import Title

register = template.Library()


@register.filter(name='random_backdrop')
def get_random_backdrop(backdrops: Iterable[str]) -> str:
    backdrop = random.choice(list(backdrops))
    return backdrop.backdrop_local.url if backdrop.backdrop_local else backdrop.backdrop_url


@register.filter(name='prepare_type')
def prepare_type_for_url(title_type: str) -> str:
    types = dict(Title.TYPE_CHOICES)
    return types.get(title_type, 'null')


@register.filter
def humanize_number(number: int) -> str | int:
    try:
        if 1_000 <= number < 1_000_000:
            result = str(number // 100 / 10).replace('.', ',') + ' тыс.'
        elif number < 1_000:
            result = str(number)
        else:
            result = str(number // 1_000_00 / 10).replace('.', ',') + ' мил.'
    except (ValueError, TypeError):
        return '—'
    return result


@register.filter(name='num_ending_firm')
def get_firm_num_ending(number: int) -> str:
    return define_firm_ending(number)


@register.filter(name='num_ending_soft')
def get_soft_num_ending(number: int) -> str:
    return define_soft_ending(number)


@register.filter
def get_item(dictionary: dict, key: int | str) -> Any:
    return dictionary.get(key)


@register.filter
def float_point(value: float) -> str | float:
    try:
        return '{0:.2f}'.format(float(value))
    except (ValueError, TypeError):
        return value


@register.filter
def python_any(values: Iterable[str]):
    return any(values) if values else []


@register.filter
def python_startswith(value: str, prefix: str) -> bool:
    return value.startswith(prefix)


@register.filter
def serialize(value: Any) -> str:
    return mark_safe(json.dumps(value))


@register.simple_tag
def exclude_params(query_params: QueryDict, to_exclude: str) -> str:
    exclude_list = to_exclude.strip().split(',')
    params = dict(query_params.lists())
    for param in exclude_list:
        params.pop(param, None)
    url = urlencode(params, doseq=True)

    return '?' + url if url else ''


@register.filter
def date_for_comment(value: datetime) -> str:
    return humanize_date_time(value)
