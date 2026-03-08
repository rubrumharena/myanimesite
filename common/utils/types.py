from dataclasses import dataclass, field
from typing import Any, NewType

from django.db.models import QuerySet

from video_player.models import VoiceOver

H = NewType('H', int)
W = NewType('W', int)

KinopoiskList = list[dict[str, Any]]


@dataclass
class EpisodeTracker:
    seasons: list[int] = field(default_factory=list)
    episodes: list[int] = field(default_factory=list)
    voiceovers: QuerySet[VoiceOver] = field(default_factory=list)
    available_episodes: list[int] = field(default_factory=list)
    available_seasons: list[int] = field(default_factory=list)
    cur_episode: int | None = None
    cur_season: int | None = None
    cur_voiceover_id: int | None = None
    time: int = 0
    video: str | None = None
