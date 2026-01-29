from django.contrib import admin

from lists.models import Collection, Folder

# Register your models here.

admin.site.register(Collection)
admin.site.register(Folder)

class CollectionAdmin(admin.ModelAdmin):
    ...


class FolderAdmin(admin.ModelAdmin):
    ...


