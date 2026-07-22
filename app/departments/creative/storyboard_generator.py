"""Storyboard stage: pick one representative shot + stock-footage search terms per scene."""

from app.config.profile_dimensions import TopicCategory
from app.models.scene import ScenePlan
from app.models.script import Script
from app.models.storyboard import Storyboard, StoryboardShot
from app.prompts.storyboard import get_shot_guidance
from app.services.documentary_llm_utils import generate_json


def build_storyboard_prompt(
    scene_plan: ScenePlan, script: Script, topic_category: TopicCategory | None = None
) -> str:
    guidance = get_shot_guidance(topic_category)
    lines_by_scene = {line.scene_index: line.text for line in script.lines}
    scene_blocks = [
        f'- scene {scene.index} ("{scene.title}"): narration = "{lines_by_scene.get(scene.index, scene.narration_beat)}"'
        for scene in scene_plan.scenes
    ]
    scenes_block = "\n".join(scene_blocks)

    return f"""You are a documentary storyboard artist choosing stock-footage shots for each scene.
Visual guidance: {guidance}

Scenes:
{scenes_block}

For each scene, describe one representative shot and 3-5 stock-footage search
terms (short, concrete, in English, suitable for searching Pexels/Pixabay).

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
    scene_plan: ScenePlan, script: Script, topic_category: TopicCategory | None = None
) -> Storyboard:
    if not scene_plan.scenes:
        return Storyboard(shots=[])
    prompt = build_storyboard_prompt(scene_plan, script, topic_category)
    data = generate_json(prompt)
    return Storyboard(shots=_parse_shots(data.get("shots", []), scene_plan))
