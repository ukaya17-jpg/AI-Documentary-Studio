"""Storyboard stage: pick one representative shot + stock-footage search terms per scene."""

from app.config.profile_dimensions import TopicCategory
from app.models.scene import ScenePlan
from app.models.script import Script
from app.models.storyboard import Storyboard, StoryboardShot
from app.prompts.storyboard import get_shot_guidance
from app.services.documentary_llm_utils import generate_json


def build_storyboard_prompt(
    scene_plan: ScenePlan,
    script: Script,
    topic_category: TopicCategory | None = None,
    topic: str = "",
    key_facts: list[str] | None = None,
) -> str:
    guidance = get_shot_guidance(topic_category)
    lines_by_scene = {line.scene_index: line.text for line in script.lines}
    scene_blocks = [
        f'- scene {scene.index} ("{scene.title}"): narration = "{lines_by_scene.get(scene.index, scene.narration_beat)}"'
        for scene in scene_plan.scenes
    ]
    scenes_block = "\n".join(scene_blocks)

    # Without an explicit topic/facts anchor, the model falls back to the
    # generic nouns in the category guidance above ("old maps", "statues")
    # verbatim, regardless of what the documentary is actually about.
    context_block = ""
    if topic:
        context_block += f"Documentary topic: {topic}\n"
    facts = [str(f).strip() for f in (key_facts or []) if f and str(f).strip()]
    if facts:
        facts_block = "\n".join(f"- {fact}" for fact in facts)
        context_block += f"Context facts:\n{facts_block}\n"
    if context_block:
        context_block += "\n"

    return f"""You are a documentary storyboard artist choosing stock-footage shots for each scene.
{context_block}Visual guidance: {guidance}

Scenes:
{scenes_block}

For each scene, describe one representative shot and 3-5 stock-footage search
terms (short, concrete, in English, suitable for searching Pexels/Pixabay).
Avoid single generic nouns (e.g. plain "map", "ship", "statue"); anchor each
term in this topic's specific era, place, or proper nouns (e.g. "Ottoman-era
map", "WWI battleship", "Gallipoli coastline", "Turkish war memorial").

Respond with a single JSON object with exactly this shape:
{{"shots": [{{"scene_index": 0, "description": "...", "shot_type": "wide|close-up|aerial|...", "search_terms": ["..."]}}]}}
Include exactly one entry per scene index listed above, in order. Do not include any other text."""


def _parse_shots(raw: list, scene_plan: ScenePlan) -> list[StoryboardShot]:
    shots_by_index: dict[int, StoryboardShot] = {}
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("scene_index"))
        except (TypeError, ValueError):
            continue
        search_terms = [str(t).strip() for t in item.get("search_terms", []) if str(t).strip()]
        shots_by_index[idx] = StoryboardShot(
            scene_index=idx,
            description=str(item.get("description", "")).strip(),
            shot_type=str(item.get("shot_type", "")).strip(),
            search_terms=search_terms,
        )

    shots = []
    for scene in scene_plan.scenes:
        shot = shots_by_index.get(scene.index)
        fallback_terms = scene.visual_keywords or [scene.title]
        if shot is None:
            shot = StoryboardShot(
                scene_index=scene.index,
                description=scene.narration_beat,
                search_terms=fallback_terms,
            )
        elif not shot.search_terms:
            shot.search_terms = fallback_terms
        shots.append(shot)
    return shots


def generate_storyboard(
    scene_plan: ScenePlan,
    script: Script,
    topic_category: TopicCategory | None = None,
    topic: str = "",
    key_facts: list[str] | None = None,
) -> Storyboard:
    if not scene_plan.scenes:
        return Storyboard(shots=[])
    prompt = build_storyboard_prompt(scene_plan, script, topic_category, topic, key_facts)
    data = generate_json(prompt)
    return Storyboard(shots=_parse_shots(data.get("shots", []), scene_plan))
