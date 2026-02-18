from django.contrib import admin

from titles.models import (Backdrop, Group, Person, Poster, RatingHistory,
                           SeasonsInfo, Statistic, Studio, Title,
                           TitleCreationHistory)

# Register your models here.

admin.site.register(Title)
admin.site.register(TitleCreationHistory)
admin.site.register(RatingHistory)
admin.site.register(Statistic)
admin.site.register(Poster)
admin.site.register(Backdrop)
admin.site.register(Studio)
admin.site.register(Person)
admin.site.register(Group)
admin.site.register(SeasonsInfo)


class TitleAdmin(admin.ModelAdmin): ...


class PosterAdmin(admin.ModelAdmin): ...


class BackdropAdmin(admin.ModelAdmin): ...
