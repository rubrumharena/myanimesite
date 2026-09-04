from modeltranslation.translator import register, TranslationOptions
from lists.models import Collection


@register(Collection)
class CollectionTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
