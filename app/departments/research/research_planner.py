"""Research stage: brainstorm key questions, facts, and narrative angles.

When app.services.web_search finds a real grounding source for the topic
(only for well-known entities/topics -- see its docstring), it's injected
into the same LLM call as a "verified source" the model is told to prefer
and not contradict. This is deliberately a single call combining grounding
and basic fact-checking, not a separate verification pass -- for most
(niche/specific) topics no source is found and behavior is identical to the
pure LLM-only research brief this stage always produced.
"""

from app.config.profile_dimensions import Tone
from app.config.templates import get_template
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
        "You are a documentary research assistant. For the topic below, produce "
        "a research brief that a scriptwriter can use to plan a short documentary."
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


def generate_research_plan(
    topic: str, tone: Tone | None = None, language: str = ""
) -> ResearchPlan:
    search_result = web_search.search_web(topic)
    prompt = build_research_prompt(topic, tone, language, web_search_result=search_result)
    data = generate_json(prompt)
    return ResearchPlan(
        topic=topic,
        key_questions=_parse_questions(data.get("key_questions", [])),
        key_facts=[str(f).strip() for f in data.get("key_facts", []) if str(f).strip()],
        angles=[str(a).strip() for a in data.get("angles", []) if str(a).strip()],
        source_snippet=search_result.abstract if search_result else "",
        source_url=search_result.source_url if search_result else "",
    )
