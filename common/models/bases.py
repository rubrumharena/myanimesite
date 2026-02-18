from django.core.validators import FileExtensionValidator
from django.db import models

from common.utils.files import resize_image, upload_to
from common.utils.types import H, W


class BaseListModel(models.Model):
    WIDTH = 640
    HEIGHT = 640
    MIN_HEIGHT = 100
    MIN_WIDTH = 100
    MAX_SIZE = 50

    name = models.CharField(max_length=40)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(
        upload_to=upload_to, null=True, blank=True, validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    titles = models.ManyToManyField('titles.Title', related_name='%(class)s_titles', blank=True)

    def save(self, *args, **kwargs):
        old_image = None
        if self.id:
            old_instance = self.__class__.objects.filter(id=self.id).first()
            if old_instance:
                old_image = old_instance.image
        super().save(*args, **kwargs)
        resize_image(new=self.image, old=old_image, resolution=(W(self.WIDTH), H(self.HEIGHT)))

    class Meta:
        abstract = True
