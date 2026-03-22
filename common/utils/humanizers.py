from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.utils import formats, timezone


def define_firm_ending(number: int) -> str:
    return pluralize(number, 'ов', '', 'а')


def define_soft_ending(number: int) -> str:
    return pluralize(number, 'й', 'я', 'и')


def humanize_date_time(date: datetime) -> str:
    today = timezone.now()
    delta = today - date
    if delta.seconds < 0:
        return ''

    months = {
        1: 'января',
        2: 'февраля',
        3: 'марта',
        4: 'апреля',
        5: 'мая',
        6: 'июня',
        7: 'июля',
        8: 'августа',
        9: 'сентября',
        10: 'октября',
        11: 'ноября',
        12: 'декабря',
    }

    minutes = 60
    delta_minutes = delta.seconds / 60
    delta_days = delta.days
    if delta_days <= 0:
        if delta_minutes <= 1:
            return 'несколько секунд назад'
        elif delta_minutes < minutes:
            total_minutes = int(delta_minutes)
            ending = pluralize(total_minutes, '', 'у', 'ы')
            return f'{total_minutes} минут{ending} назад'
        elif today.date() == date.date():
            return date.strftime('сегодня в %H:%M')
    elif delta_days == 1:
        return date.strftime('вчера в %H:%M')
    else:
        return formats.date_format(date, f'd {months[date.month]} Y в H:i')


def format_subscription_period(ends_at):
    now = timezone.now()
    delta = relativedelta(ends_at, now)

    months = delta.months
    days = delta.days
    hours = delta.hours

    parts = []

    if not days and not months and hours >= 0:
        parts.append('сегодня')
    elif days > 1 and not months:
        parts.append(f'{days} {pluralize(days, "дней", "день", "дня")}')
        parts.append(f'{hours} {pluralize(hours, "часов", "час", "часа")}')
    else:
        parts.append(f'{months} {pluralize(months, "месяцев", "месяц", "месяца")}')
        if days:
            parts.append(f'{days} {pluralize(days, "дней", "ден", "дня")}')

    return ' '.join(parts)


def pluralize(number: int, form1: str, form2: str, form3: str) -> str:
    if not str(number).isdigit():
        return ''
    number = int(number)

    if (11 <= number <= 19) or number % 10 == 0 or number % 10 >= 5:
        ending = form1
    elif number % 10 == 1:
        ending = form2
    else:
        ending = form3
    return ending
