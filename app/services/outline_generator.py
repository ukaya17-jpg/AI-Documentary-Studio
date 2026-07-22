"""Outline stage: turn a topic + research plan into a structured documentary outline."""

from app.config.profile_dimensions import TopicCategory
from app.config.templates import get_template
from app.models.outline import Outline, OutlineSection
from app.models.research_plan import ResearchPlan
from app.services.documentary_llm_utils import generate_json


def _research_brief(research_plan: ResearchPlan | None) -> str:
    if research_plan is None:
        return ""
    facts = "\n".join(f"- {f}" for f in research_plan.key_facts)
    questions = "\n".join(f"- {q.question}" for q in research_plan.key_questions)
    angles = "\n".join(f"- {a}" for a in research_plan.angles)
    parts = []
    if facts:
        parts.append(f"Key facts:\n{facts}")
    if questions:
        parts.append(f"Key questions:\n{questions}")
    if angles:
        parts.append(f"Narrative angles:\n{angles}")
    return "\n\n".join(parts)


def build_outline_prompt(
    topic: str,
    research_plan: ResearchPlan | None = None,
    topic_category: TopicCategory | None = None,
    language: str = "",
) -> str:
    template = get_template(topic_category)
    prompt = (
        "You are a documentary outline writer.\n"
        f"Style: {template['style']}\n"
        f"Opening hook guidance: {template['opening_hook']}\n"
        f"Section guidance: {template['section_guidance']}\n"
        f"Closing guidance: {template['closing']}\n\n"
        f'Topic: "{topic}"'
    )
    brief = _research_brief(research_plan)
    if brief:
        prompt += f"\n\nResearch brief:\n{brief}"
    if language and language != "auto":
        prompt += f"\n\nRespond in language: {language}"
    prompt += """

Produce a documentary outline as a single JSON object with exactly this shape:
{
  "title": "...",
  "hook": "...",
  "sections": [{"title": "...", "summary": "...", "key_points": ["..."], "importance": 1}],
  "closing": "..."
}
Produce 4-7 sections ordered narratively. Rate each section's "importance" from
1 (skippable) to 5 (essential) so a downstream step can trim sections for a
shorter cut. Do not include any other text."""
    return prompt


def _parse_sections(raw: list) -> list[OutlineSection]:
    sections = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        try:
            importance = int(item.get("importance", 3))
        except (TypeError, ValueError):
            importance = 3
        importance = max(1, min(5, importance))
        sections.append(
            OutlineSection(
                title=title,
                summary=str(item.get("summary", "")).strip(),
                key_points=[
                    str(p).strip() for p in item.get("key_points", []) if str(p).strip()
                ],
                importance=importance,
            )
        )
    return sections


def generate_outline(
    topic: str,
    research_plan: ResearchPlan | None = None,
    topic_category: TopicCategory | None = None,
    language: str = "",
) -> Outline:
    prompt = build_outline_prompt(topic, research_plan, topic_category, language)
    data = generate_json(prompt)
    return Outline(
        title=str(data.get("title", "")).strip() or topic,
        hook=str(data.get("hook", "")).strip(),
        sections=_parse_sections(data.get("sections", [])),
        closing=str(data.get("closing", "")).strip(),
    )
