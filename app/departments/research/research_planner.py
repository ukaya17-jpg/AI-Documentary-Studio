"""Research stage: brainstorm key questions, facts, and narrative angles.

When app.services.web_search finds a real grounding source for the topic
(only for well-known entities/topics -- see its docstring), it's injected
into the same LLM call as a "verified source" the model is told to prefer
and not contradict. This is deliberately a single call combining grounding
and basic fact-checking, not a separate verification pass -- for most
(niche/specific) topics no source is found and behavior is identical to the
pure LLM-only research brief this stage always produced.

Real production bug found and fixed here: a bare/ambiguous topic (e.g.
"Roma") can resolve, via DuckDuckGo/Wikipedia lookup, to a same-named but
unrelated real-world entity -- a real generation for topic "Roma" (topic_
category already resolved to "history") got grounded in AS Roma the
football club's Wikipedia page, and the whole outline/script ended up being
about the football club instead of the city, because the grounding text was
force-fed into the LLM as a "verified source ... do not contradict." See
_grounding_matches_category(): grounding is discarded (treated as ungrounded,
the existing/expected degrade path) when its own text gives a clear keyword
signal for a category OTHER than the one already assigned to the topic.
"""

from loguru import logger

from app.config.profile_dimensions import Tone, TopicCategory
from app.config.templates import get_template
from app.departments.research.intent_analyzer import CATEGORY_KEYWORDS
from app.models.research_plan import ResearchPlan, ResearchQuestion
from app.models.web_search import WebSearchResult
from app.services import web_search
from app.services.documentary_llm_utils import generate_json


def build_research_prompt(
    topic: str,
    tone: Tone | None = None,
    language: str = "",
    web_search_result: WebSearchResult | None = None,
) -> str:
    style = get_template(tone)["style"] if tone else ""
    prompt = (
        "You are a YouTube video research assistant. For the topic below, produce "
        "a research brief that a scriptwriter can use to plan a fast-paced, "
        "high-retention YouTube video."
        f'\n\nTopic: "{topic}"'
    )
    if style:
        prompt += f"\nStyle guidance: {style}"
    if web_search_result:
        prompt += (
            f"\n\nVerified web source ({web_search_result.source_url or 'web search'}):\n"
            f"{web_search_result.abstract}\n"
            "Prefer key_facts that are consistent with this source. Do not include "
            "key_facts that contradict it."
        )
    if language and language != "auto":
        prompt += f"\nRespond in language: {language}"
    prompt += """

Respond with a single JSON object with exactly this shape:
{
  "key_questions": [{"question": "...", "rationale": "..."}],
  "key_facts": ["..."],
  "angles": ["..."]
}
Produce 3-5 key_questions, 5-8 key_facts, and 2-4 narrative angles
(distinct ways to frame the story). Do not include any other text."""
    return prompt


def _parse_questions(raw: list) -> list[ResearchQuestion]:
    questions = []
    for item in raw or []:
        if isinstance(item, dict):
            questions.append(
                ResearchQuestion(
                    question=str(item.get("question", "")).strip(),
                    rationale=str(item.get("rationale", "")).strip(),
                )
            )
        elif item:
            questions.append(ResearchQuestion(question=str(item).strip()))
    return [q for q in questions if q.question]


def _grounding_matches_category(
    search_result: WebSearchResult, topic_category: TopicCategory | None
) -> bool:
    """False only when the grounding text gives a clear keyword signal for a
    DIFFERENT category than topic_category and no signal at all for
    topic_category itself -- e.g. an abstract about "a professional football
    club" when the topic was categorized as "history", not "sports". When
    topic_category is unknown, or the text is simply inconclusive either way
    (no category keywords at all), the grounding is accepted as before --
    this only guards against a positive, legible mismatch.
    """
    if topic_category is None:
        return True
    text = f"{search_result.heading} {search_result.abstract}".lower()
    if any(keyword in text for keyword in CATEGORY_KEYWORDS.get(topic_category, [])):
        return True
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category != topic_category and any(keyword in text for keyword in keywords):
            return False
    return True


def generate_research_plan(
    topic: str,
    tone: Tone | None = None,
    language: str = "",
    topic_category: TopicCategory | None = None,
) -> ResearchPlan:
    search_result = web_search.search_web(topic, language=language)
    if search_result and not _grounding_matches_category(search_result, topic_category):
        logger.warning(
            f"research_planner: discarding grounding source {search_result.source_url!r} "
            f"for topic={topic!r} -- its text signals a different category than the "
            f"resolved topic_category={topic_category!r}, treating as ungrounded"
        )
        search_result = None
    prompt = build_research_prompt(topic, tone, language, web_search_result=search_result)
    data = generate_json(prompt)
    return ResearchPlan(
        topic=topic,
        key_questions=_parse_questions(data.get("key_questions", [])),
        key_facts=[str(f).strip() for f in data.get("key_facts", []) if str(f).strip()],
        angles=[str(a).strip() for a in data.get("angles", []) if str(a).strip()],
        source_snippet=search_result.abstract if search_result else "",
        source_url=search_result.source_url if search_result else "",
        grounded=search_result is not None,
    )
