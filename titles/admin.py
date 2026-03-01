from django.contrib import admin
from django.shortcuts import redirect

from services.kinopoisk_import import create_from_title_ids
from titles.models import (
    Backdrop,
    Group,
    Person,
    Poster,
    RatingHistory,
    SeasonsInfo,
    Statistic,
    Studio,
    Title,
    TitleImportLog,
)

# Register your models here.


admin.site.register(TitleImportLog)
admin.site.register(RatingHistory)
admin.site.register(Statistic)
admin.site.register(Poster)
admin.site.register(Backdrop)
admin.site.register(Studio)
admin.site.register(Person)
admin.site.register(Group)
admin.site.register(SeasonsInfo)


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    def add_view(self, request, form_url='', extra_context=None):
        if request.method == 'POST':
            kinopoisk_id = request.POST.get('kinopoisk_id')
            if kinopoisk_id:
                existing = Title.objects.filter(kinopoisk_id=kinopoisk_id).first()

                if not existing:
                    create_from_title_ids([int(kinopoisk_id)])
                    existing = Title.objects.get(kinopoisk_id=kinopoisk_id)

                return redirect(f'/admin/titles/title/{existing.pk}/change/')

        return super().add_view(request, form_url, extra_context)


class PosterAdmin(admin.ModelAdmin): ...


class BackdropAdmin(admin.ModelAdmin): ...
