"""Intent stage: resolve topic category (auto-detect + user override) and language."""

from loguru import logger

from app.config.profile_dimensions import Language, TopicCategory, resolve_topic_category
from app.services.documentary_llm_utils import generate_json

_TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")

_CATEGORY_KEYWORDS = {
    TopicCategory.space: [
        "space", "galaxy", "planet", "nasa", "universe", "astronomy",
        "mars", "moon", "star", "rocket", "cosmos", "orbit",
        "uzay", "gezegen", "yıldız", "evren", "galaksi", "roket",
    ],
    TopicCategory.psychology: [
        "psychology", "brain", "mind", "behavior", "cognitive",
        "psikoloji", "beyin", "davranış", "zihin",
    ],
    TopicCategory.travel: [
        "travel", "city", "country", "destination", "trip",
        "seyahat", "şehir", "ülke", "gezi", "tatil",
    ],
    TopicCategory.history: [
        "history", "war", "empire", "ancient", "civilization",
        "tarih", "savaş", "imparatorluk", "medeniyet",
    ],
}


def detect_language(topic: str) -> str:
    if any(ch in _TURKISH_CHARS for ch in topic):
        return Language.tr.value
    return Language.en.value


def _heuristic_category(topic: str) -> TopicCategory:
    lowered = topic.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return TopicCategory.history


def _build_category_prompt(topic: str) -> str:
    categories = ", ".join(c.value for c in TopicCategory)
    return (
        "Classify the following documentary video topic into exactly one "
        f"category from this fixed list: {categories}.\n\n"
        f'Topic: "{topic}"\n\n'
        f'Respond with a single JSON object: {{"category": "<one of {categories}>"}}. '
        "Do not include any other text."
    )


def detect_topic_category(topic: str) -> TopicCategory:
    try:
        data = generate_json(_build_category_prompt(topic))
        category = resolve_topic_category(data.get("category"))
        if category is not None:
            return category
        logger.warning(
            f"intent_analyzer: LLM returned unrecognized category {data.get('category')!r}, "
            "falling back to heuristic"
        )
    except Exception as e:
        logger.warning(f"intent_analyzer: LLM category detection failed, falling back to heuristic: {e}")
    return _heuristic_category(topic)


def analyze_intent(
    topic: str,
    language: str = "auto",
    topic_category_override: TopicCategory | str | None = None,
) -> dict:
    """Resolve the final language and topic category for a documentary project.

    ``topic_category_override`` wins whenever it resolves to a valid category
    (the WebUI's manual override); otherwise the category is auto-detected.
    """
    resolved_language = (
        language if language and language != Language.auto.value else detect_language(topic)
    )
    override = resolve_topic_category(topic_category_override)
    resolved_category = override or detect_topic_category(topic)
    return {"language": resolved_language, "topic_category": resolved_category}
