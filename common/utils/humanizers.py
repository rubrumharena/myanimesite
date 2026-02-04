from datetime import datetime

from django.utils import formats, timezone


def define_firm_ending(number: int) -> str:
    if not str(number).isdigit():
        return ''
    number = int(number)

    if number in list(range(11, 20)) or number % 10 == 0 or number % 10 >= 5:
        ending = 'ов'
    elif number % 10 == 1:
        ending = ''
    else:
        ending = 'а'
    return ending


def define_soft_ending(number: int) -> str:
    if not str(number).isdigit():
        return ''
    number = int(number)

    if number in list(range(11, 20)) or number % 10 == 0 or number % 10 >= 5:
        ending = 'й'
    elif number % 10 == 1:
        ending = 'я'
    else:
        ending = 'и'
    return ending


def humanize_date_time(date: datetime) -> str:
    def _get_num_ending(number: int) -> str:
        if not str(number).isdigit():
            return ''
        number = int(number)

        if number in list(range(11, 20)) or number % 10 == 0 or number % 10 >= 5:
            ending = ''
        elif number % 10 == 1:
            ending = 'у'
        else:
            ending = 'ы'

        return ending

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
            ending = _get_num_ending(total_minutes)
            return f'{total_minutes} минут{ending} назад'
        elif today.date() == date.date():
            return date.strftime('сегодня в %H:%M')
    elif delta_days == 1:
        return date.strftime('вчера в %H:%M')
    else:
        return formats.date_format(date, f'd {months[date.month]} Y в H:i')
