from typing import Callable

from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.core.files.uploadedfile import UploadedFile
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext as _


def validate_rating(rating: str | int | float) -> None:
    try:
        check_single_rating_part(float(rating))
    except ValueError:
        if rating.count('-') < 0 or rating.count('-') > 1:
            raise ValidationError('Could not read the range! The range must look like 1-10')

        rating_range = rating.split('-')

        try:
            for rating_limit in rating_range:
                check_single_rating_part(float(rating_limit))

            if float(rating_range[0]) >= float(rating_range[1]):
                raise ValidationError('Incorrect range')
        except ValueError:
            raise ValidationError(f'{rating} is unsupported value! The range is 1-10')
        except IndexError:
            ...


def validate_years(year: str | int) -> None:
    year = str(year)
    if year.isdigit():
        check_single_years_part(year)
        return None

    try:
        if int(year) <= 0:
            check_single_years_part(year)
            return None
    except ValueError:
        ...

    if year.count('-') < 0 or year.count('-') > 1:
        raise ValidationError('Could not read the range! The range must look like 1874-2050')

    year_range = year.split('-')

    try:
        for year_limit in year_range:
            check_single_years_part(year_limit)
        if int(year_range[0]) >= int(year_range[1]):
            raise ValidationError('Incorrect range')
    except ValueError:
        raise ValidationError(f'{year} is unsupported value! The range is 1874-2050')
    except IndexError:
        ...
    return None


def check_single_years_part(year: str) -> None:
    if not str(year).strip().isdigit():
        raise ValidationError(f'{year} is unsupported value! The range is 1874-2050')
    if 1874 > int(year) or int(year) > 2050:
        raise ValidationError(f'{year} is out of range! The range is 1874-2050')


def check_single_rating_part(rating: float) -> float:
    if rating > 10 or rating <= 0:
        raise ValidationError(f'{rating} is out of range! The range is 1-10')
    return rating


@deconstructible
class ValidateImageSize:
    def __init__(self, max_size_mb, min_width, min_height):
        self.max_size_mb = max_size_mb
        self.min_width = min_width
        self.min_height = min_height

    def __call__(self, image):
        ...

    def __eq__(self, other):
        return (
            isinstance(other, ValidateImageSize)
            and (self.max_size_mb, self.min_width, self.min_height)
            == (other.max_size_mb, other.min_width, other.min_height)
        )