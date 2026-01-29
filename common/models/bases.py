from django.db import models

from common.utils.files import resize_image


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

    def save(self, *args, **kwargs):
        old_image = None
        if self.id:
            old_image = self.__class__.objects.filter(id=self.id).values_list('image', flat=True).first()
        super().save(*args, **kwargs)
        resize_image(new=self.image, old=old_image, resolution=(self.WIDTH, self.HEIGHT))

    class Meta:
        abstract = True