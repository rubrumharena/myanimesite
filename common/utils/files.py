import os
from typing import Iterable, Optional

from django.db.models.fields.files import ImageFieldFile, FieldFile
from PIL import Image, ImageOps


def delete_orphaned_files(*args):
    for arg in args:
        if isinstance(arg, Iterable) and not isinstance(arg, (str, bytes, FieldFile)):
            files = arg
        else:
            files = (arg,)
        for file in files:
            try:
                os.remove(file.path)
            except (OSError, FileNotFoundError, AttributeError, ValueError):
                ...


def resize_image(
    resolution: tuple[int, int], new: Optional[ImageFieldFile] = None, old: Optional[ImageFieldFile] = None
) -> bool | str:
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
