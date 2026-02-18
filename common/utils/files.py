import os
import uuid
from typing import Iterable

from django.db.models.fields.files import FieldFile, ImageFieldFile
from PIL import Image, ImageOps

from common.utils.types import H, W


def delete_orphaned_files(*args: Iterable[FieldFile]) -> None:
    for file in args:
        try:
            os.remove(file.path)
        except (OSError, FileNotFoundError, AttributeError, ValueError):
            ...


def resize_image(resolution: tuple[W, H], new: ImageFieldFile | None = None, old: ImageFieldFile | None = None) -> bool:
    if new and new != old:
        if old:
            old.delete(save=False)
        path = new.path
        original = Image.open(path)

        width, height = resolution
        if original.size[0] > width or original.size[1] > height:
            resized = ImageOps.fit(original, resolution, centering=(0.5, 0.5))
            resized.save(path)
        return True
    elif old and not new:
        old.delete()
        return False
    return False


def upload_to(instance, filename):
    ext = filename.split('.')[-1]
    return f'{instance._meta.model_name}/{uuid.uuid4()}.{ext}'
