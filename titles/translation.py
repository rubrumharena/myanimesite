from modeltranslation.translator import TranslationOptions, register

from titles.models import Person, Title


@register(Title)
class TitleTranslationOptions(TranslationOptions):
    fields = ('name', 'overview', 'tagline')


@register(Person)
class PersonTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
