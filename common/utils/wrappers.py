from functools import wraps
from http import HTTPStatus
from typing import Callable

from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest, JsonResponse
from django.shortcuts import reverse


def superuser_required(user: AbstractUser) -> bool:
    return user.is_active and user.is_superuser


def login_required_ajax(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(data={'redirect': reverse('accounts:welcome')}, status=HTTPStatus.UNAUTHORIZED)
        return func(request, *args, **kwargs)

    return wrapper
