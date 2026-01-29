import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from http import HTTPStatus
from typing import List, Optional, Any, Dict


from PIL import Image, ImageOps
from django.db.models.fields.files import ImageFieldFile
from django.http import JsonResponse
from django.utils import timezone, formats
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
