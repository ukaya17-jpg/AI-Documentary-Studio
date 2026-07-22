"""Thinking Layer: turn raw/vague viewer input into a well-formed documentary topic.

Sits upstream of the 12-stage pipeline, not inside it: callers with an
already-clean topic (tests, CLI, programmatic callers) can skip this and call
`app.pipeline.default_pipeline.run_pipeline(topic=...)` directly. This does
not decide language or topic category -- that stays IntentAnalyzer's job
downstream, so the two never overlap.
"""

from loguru import logger

from app.models.idea import IdeaCandidate
from app.services.documentary_llm_utils import generate_json

_MAX_RETRIES = 3


def build_idea_prompt(raw_input: str) -> str:
    return f"""You are a documentary topic editor. A viewer typed the following
raw idea or question. Rewrite it as a single, concrete, well-formed
documentary topic title in the SAME language as the input, plus a one-sentence
angle describing what makes it a compelling documentary.

Raw input: "{raw_input}"

Respond with a single JSON object with exactly this shape:
{{"topic": "...", "angle": "..."}}
Do not include any other text."""


def generate_idea(raw_input: str) -> IdeaCandidate:
    raw_input = (raw_input or "").strip()
    if not raw_input:
        raise ValueError("raw_input must not be empty")

    prompt = build_idea_prompt(raw_input)
    try:
        data = generate_json(prompt, max_retries=_MAX_RETRIES)
        topic = str(data.get("topic", "")).strip()
        if not topic:
            raise ValueError("idea_generator: LLM returned an empty topic")
        return IdeaCandidate(topic=topic, angle=str(data.get("angle", "")).strip())
    except Exception as e:
        # Graceful degradation: hand the raw input through unchanged rather
        # than blocking the whole flow on a topic-refinement failure.
        logger.warning(f"idea_generator: LLM refinement failed, using raw input verbatim: {e}")
        return IdeaCandidate(topic=raw_input, angle="")
