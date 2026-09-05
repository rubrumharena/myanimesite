from modeltranslation.translator import TranslationOptions, register

from lists.models import Collection


@register(Collection)
class CollectionTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
