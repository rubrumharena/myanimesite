from functools import wraps
from http import HTTPStatus

from django.http import JsonResponse
from django.shortcuts import reverse


def superuser_required(user) -> bool:
    return user.is_active and user.is_superuser


def login_required_ajax(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(data={'redirect': reverse('accounts:welcome')}, status=HTTPStatus.UNAUTHORIZED)
        return func(request, *args, **kwargs)

    return wrapper
