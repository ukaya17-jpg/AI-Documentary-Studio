"""Script stage: write per-scene narration lines sized to each scene's duration budget."""

from app.models.scene import ScenePlan
from app.models.script import Script, ScriptLine
from app.services.documentary_llm_utils import generate_json

_WORDS_PER_SECOND = 2.3

DEFAULT_SCRIPT_SYSTEM_PROMPT = (
    "You are a documentary narration scriptwriter. Write natural, spoken-style "
    "narration -- no markdown, no scene labels, no 'narrator says'."
)


def build_script_prompt(
    scene_plan: ScenePlan,
    topic: str,
    language: str = "",
    custom_system_prompt: str = "",
) -> str:
    scene_lines = []
    for scene in scene_plan.scenes:
        target_words = max(5, round(scene.duration_seconds * _WORDS_PER_SECOND))
        scene_lines.append(
            f'- scene {scene.index} ("{scene.title}"): {scene.narration_beat} '
            f"[~{target_words} words, ~{scene.duration_seconds:.0f}s]"
        )
    scenes_block = "\n".join(scene_lines)

    prompt = custom_system_prompt or DEFAULT_SCRIPT_SYSTEM_PROMPT
    prompt += f"""

Topic: "{topic}"

Write one narration line per scene below, matching its target word count as
closely as possible so the timing lines up with the scene's on-screen duration:
{scenes_block}"""
    if language and language != "auto":
        prompt += f"\n\nRespond in language: {language}"
    prompt += """

Respond with a single JSON object with exactly this shape:
{"lines": [{"scene_index": 0, "text": "..."}]}
Include exactly one entry per scene index listed above, in order. Do not include
any other text, markdown, or scene titles inside the narration text itself."""
    return prompt


def _parse_lines(raw: list) -> dict[int, str]:
    lines_by_index = {}
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("scene_index"))
        except (TypeError, ValueError):
            continue
        text = str(item.get("text", "")).strip()
        if text:
            lines_by_index[idx] = text
    return lines_by_index


def generate_script(
    scene_plan: ScenePlan,
    topic: str,
    language: str = "",
    custom_system_prompt: str = "",
) -> Script:
    if not scene_plan.scenes:
        return Script(full_text="", lines=[], language=language)

    prompt = build_script_prompt(scene_plan, topic, language, custom_system_prompt)
    data = generate_json(prompt)
    lines_by_index = _parse_lines(data.get("lines", []))

    lines = [
        ScriptLine(scene_index=scene.index, text=lines_by_index.get(scene.index) or scene.narration_beat)
        for scene in scene_plan.scenes
    ]
    full_text = "\n\n".join(line.text for line in lines)
    return Script(full_text=full_text, lines=lines, language=language)
