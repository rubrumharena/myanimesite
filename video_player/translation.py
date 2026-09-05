from modeltranslation.translator import TranslationOptions, register

from video_player.models import VoiceOver


@register(VoiceOver)
class VoiceOverTranslationOptions(TranslationOptions):
    fields = ('name',)
