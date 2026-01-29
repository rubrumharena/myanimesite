import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from http import HTTPStatus
from typing import List, Optional, Any, Dict, Iterable

from PIL import Image, ImageOps
from django.db.models.fields.files import ImageFieldFile
from django.http import JsonResponse
from django.utils import timezone, formats
from django.shortcuts import reverse




def delete_orphaned_files(*args):
    for arg in args:
        if isinstance(arg, Iterable) and not isinstance(arg, (str, bytes)):
            files = arg
        else:
            files = (arg,)
        print(files)
        for file in files:
            try:
                os.remove(file.path)
            except (OSError, FileNotFoundError, AttributeError, ValueError):
                ...

def resize_image(resolution: tuple[int, int], new: Optional[ImageFieldFile]=None, old: Optional[ImageFieldFile]=None) -> bool|str:
    if new and new != old:
        if old:
            old.delete(save=False)
        path = new.path
        original = Image.open(path)
        if original.size[0] > max(resolution) or original.size[1] > max(resolution):
            resized = ImageOps.fit(original, resolution, centering=(0.5, 0.5))
            resized.save(path)
        return True
    elif old and not new:
        old.delete()
        return False
    return False