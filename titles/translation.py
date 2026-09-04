from modeltranslation.translator import register, TranslationOptions
from titles.models import Title, Person


@register(Title)
class TitleTranslationOptions(TranslationOptions):
    fields = ('name', 'overview', 'tagline')

@register(Person)
class PersonTranslationOptions(TranslationOptions):
    fields = ('name', 'description')