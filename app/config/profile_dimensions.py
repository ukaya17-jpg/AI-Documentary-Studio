"""Documentary pipeline profile dimensions: topic category, pacing, language."""

from enum import Enum


class TopicCategory(str, Enum):
    travel = "travel"
    history = "history"
    space = "space"
    psychology = "psychology"


class Tone(str, Enum):
    cinematic = "cinematic"
    credibility = "credibility"
    epic = "epic"
    scientific = "scientific"
    neutral = "neutral"


# One default tone per topic category, chosen to match each category's
# existing PROFILE_PROMPTS template exactly (travel=cinematic,
# history=credibility, space=epic, psychology=scientific) -- resolve_tone()
# with no override must reproduce today's category-locked behavior.
DEFAULT_TONE_BY_CATEGORY = {
    TopicCategory.travel: Tone.cinematic,
    TopicCategory.history: Tone.credibility,
    TopicCategory.space: Tone.epic,
    TopicCategory.psychology: Tone.scientific,
}


class Format(str, Enum):
    """What kind of content this is (independent of Tone, which is how it
    sounds, and Pacing, which is how long/fast it is). Only `educational` is
    implemented -- podcast/kids/corporate are deliberately not modeled here
    yet; see PROGRESS.md for why each needs its own separate decision.
    """

    educational = "educational"


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


def resolve_tone(
    topic_category: str | TopicCategory | None,
    tone_override: str | Tone | None = None,
) -> Tone:
    if tone_override not in (None, ""):
        if isinstance(tone_override, Tone):
            return tone_override
        try:
            return Tone(str(tone_override).strip().lower())
        except ValueError:
            pass  # invalid override string -- fall through to the category default
    category = resolve_topic_category(topic_category)
    return DEFAULT_TONE_BY_CATEGORY.get(category, Tone.neutral)


def resolve_format(value: str | Format | None) -> Format | None:
    if value is None or value == "":
        return None
    if isinstance(value, Format):
        return value
    try:
        return Format(str(value).strip().lower())
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
