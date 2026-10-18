import io
import os
import uuid
from typing import Iterable

from django.core.files.base import ContentFile
from django.db.models.fields.files import FieldFile, ImageFieldFile
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from common.utils.types import H, W

# Без этого Pillow не открывает HEIC/HEIF с iPhone и ImageField считает файл битым
register_heif_opener()

ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'heic', 'heif']
HEIF_FORMATS = ('HEIF', 'HEIC')


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


def convert_heif_to_jpeg(file):
    """HEIC показывает только Safari, поэтому храним такие картинки как JPEG."""
    image = getattr(file, 'image', None)
    if image is None or (image.format or '').upper() not in HEIF_FORMATS:
        return file

    file.seek(0)
    converted = ImageOps.exif_transpose(Image.open(file)).convert('RGB')
    buffer = io.BytesIO()
    converted.save(buffer, format='JPEG', quality=90)

    name = f'{os.path.splitext(os.path.basename(file.name))[0]}.jpg'
    return ContentFile(buffer.getvalue(), name=name)


def upload_to(instance, filename):
    ext = filename.split('.')[-1]
    return f'{instance._meta.model_name}/{uuid.uuid4()}.{ext}'
