from modeltranslation.translator import register, TranslationOptions
from video_player.models import VoiceOver


@register(VoiceOver)
class VoiceOverTranslationOptions(TranslationOptions):
    fields = ('name', )
