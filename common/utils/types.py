from dataclasses import dataclass, field
from typing import NewType

H = NewType('H', int)
W = NewType('W', int)


@dataclass
class EpisodeTracker:
    seasons: list[int] = field(default_factory=list)
    episodes: list[int] = field(default_factory=list)
    voiceovers: list[int] = field(default_factory=list)
    available_episodes: list[int] = field(default_factory=list)
    available_seasons: list[int] = field(default_factory=list)
    cur_episode: int | None = None
    cur_season: int | None = None
    cur_voiceover: int | None = None
    time: int = 0
    video: str | None = None
