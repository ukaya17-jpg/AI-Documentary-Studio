"""Research stage: brainstorm key questions, facts, and narrative angles.

There is no live web-search tool wired into this app, so "research" here means
asking the LLM to structure what it already knows about the topic into a brief
that the outline stage can build on -- not fetching live sources.
"""

from app.config.profile_dimensions import TopicCategory
from app.config.templates import get_template
from app.models.research_plan import ResearchPlan, ResearchQuestion
from app.services.documentary_llm_utils import generate_json


def build_research_prompt(
    topic: str, topic_category: TopicCategory | None = None, language: str = ""
) -> str:
    style = get_template(topic_category)["style"] if topic_category else ""
    prompt = (
        "You are a documentary research assistant. For the topic below, produce "
        "a research brief that a scriptwriter can use to plan a short documentary."
        f'\n\nTopic: "{topic}"'
    )
    if style:
        prompt += f"\nStyle guidance: {style}"
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
    topic: str, topic_category: TopicCategory | None = None, language: str = ""
) -> ResearchPlan:
    prompt = build_research_prompt(topic, topic_category, language)
    data = generate_json(prompt)
    return ResearchPlan(
        topic=topic,
        key_questions=_parse_questions(data.get("key_questions", [])),
        key_facts=[str(f).strip() for f in data.get("key_facts", []) if str(f).strip()],
        angles=[str(a).strip() for a in data.get("angles", []) if str(a).strip()],
    )
