from django.contrib import admin

from video_player.models import Bucket, VideoResource, ViewingHistory, VoiceOver

# Register your models here.

admin.site.register(VoiceOver)
admin.site.register(ViewingHistory)
admin.site.register(VideoResource)
admin.site.register(Bucket)
