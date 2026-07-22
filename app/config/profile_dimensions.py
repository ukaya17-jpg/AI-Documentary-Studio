"""Documentary pipeline profile dimensions: topic category, pacing, language."""

from enum import Enum


class TopicCategory(str, Enum):
    travel = "travel"
    history = "history"
    space = "space"
    psychology = "psychology"


class Pacing(str, Enum):
    short = "short"
    long = "long"


class Language(str, Enum):
    auto = "auto"
    tr = "tr"
    en = "en"


# Scene count / per-scene duration budget used by ScenePlanner, keyed by pacing.
PACING_SCENE_SPEC = {
    Pacing.short: {"scene_count": 4, "scene_duration": 5.0},
    Pacing.long: {"scene_count": 7, "scene_duration": 8.0},
}


def resolve_topic_category(value: str | TopicCategory | None) -> TopicCategory | None:
    if value is None or value == "":
        return None
    if isinstance(value, TopicCategory):
        return value
    try:
        return TopicCategory(str(value).strip().lower())
    except ValueError:
        return None


def resolve_pacing(value: str | Pacing | None, default: Pacing = Pacing.short) -> Pacing:
    if value is None or value == "":
        return default
    if isinstance(value, Pacing):
        return value
    try:
        return Pacing(str(value).strip().lower())
    except ValueError:
        return default
