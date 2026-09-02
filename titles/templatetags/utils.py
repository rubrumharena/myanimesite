import json
import random
import html
import re
from datetime import datetime
from typing import Any, Iterable

from django import template
from django.http import QueryDict
from django.utils.safestring import mark_safe

from common.utils.enums import COLORS
from common.utils.humanizers import define_firm_ending, define_soft_ending, humanize_date_time
from common.utils.tools import exclude_params as ep
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
    return ep(query_params, to_exclude)


@register.filter
def date_for_comment(value: datetime) -> str:
    return humanize_date_time(value)


@register.filter(name='prepare')
def prepare_backdrop(backdrop) -> str:
    return backdrop.backdrop_local.url if backdrop.backdrop_local else backdrop.backdrop_url


@register.filter
def render_markup(text: str) -> str:
    if not text:
        return ''

    out: str = html.escape(str(text))

    out = re.sub(
        r'\[(.+?)\]\((https?://[^\s)]+)\)',
        r'<a href="\2" target="_blank" rel="noopener nofollow" class="z-10 !text-(--accent) hover:underline">\1</a>',
        out,
    )
    out = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', out)
    out = re.sub(r'(?<!\*)\*(?!\*)([^*\n]+)\*(?!\*)', r'<em>\1</em>', out)
    out = re.sub(
        r'\|\|(.+?)\|\|',
        r'<span class="spoiler cursor-pointer select-none rounded px-1 blur-[4px] '
        r'transition-[filter,background-color] duration-300 bg-neutral-800/60" '
        r'title="Нажмите, чтобы показать">\1</span>',
        out,
        flags=re.S,
    )
    out = re.sub(
        r'^&gt; (.+)$',
        r'<span class="block border-l-2 border-neutral-700 pl-3 !text-neutral-400">\1</span>',
        out,
        flags=re.M,
    )
    out = out.replace('\n', '<br>')

    return mark_safe(out)


@register.filter
def status_accent(value):
    return COLORS.get(value, 'var(--color-neutral-400)')


@register.filter
def rating_color(value):
    if not value:
        return 'var(--color-neutral-400)'

    t = (max(1.0, min(10.0, float(value))) - 1) / 9

    lightness = 63.7 + (78.9 - 63.7) * t
    chroma = 0.237 + (0.154 - 0.237) * t
    hue = 25.3 + (211.5 - 25.3) * t

    return f'oklch({lightness:.1f}% {chroma:.3f} {hue:.1f})'


@register.filter
def star_fill(rating: float | int, stars: int = 10) -> dict[int, int]:
    rating = float(rating)
    stars = int(stars)
    if rating > stars:
        raise ValueError('The number must equal or less than the number of stars')
    if rating < 0:
        raise ValueError('The number must be positive')
    filled_rating = {}
    full_stars = int(rating)

    partial = int(round((rating - full_stars) * 100))

    for star in range(1, stars + 1):
        if star <= full_stars:
            filled_rating[star] = 100
        elif star == full_stars + 1 and partial:
            filled_rating[star] = partial
        else:
            filled_rating[star] = 0

    return filled_rating


@register.filter
def rating_fill_class(rating) -> str:
    rating = float(rating or 0)
    if not rating:
        return 'fill-neutral-700'
    if rating < 5:
        return 'fill-red-500'
    if rating < 7:
        return 'fill-yellow-300'
    if rating < 9:
        return 'fill-green-500'
    return 'fill-(--accent)'
