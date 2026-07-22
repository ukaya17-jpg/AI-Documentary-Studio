"""Scene stage: turn an outline into a pacing-budgeted scene plan.

Purely deterministic (no LLM call): pacing fixes the scene count and
per-scene duration, and the highest-importance outline sections are kept,
in their original narrative order.
"""

from app.config.profile_dimensions import PACING_SCENE_SPEC, Pacing
from app.models.outline import Outline, OutlineSection
from app.models.scene import Scene, ScenePlan


def _select_sections_by_importance(
    sections: list[OutlineSection], scene_count: int
) -> list[OutlineSection]:
    ranked = sorted(enumerate(sections), key=lambda pair: (-pair[1].importance, pair[0]))
    kept_original_indices = {i for i, _ in ranked[:scene_count]}
    return [section for i, section in enumerate(sections) if i in kept_original_indices]


def plan_scenes(outline: Outline, pacing: Pacing = Pacing.short) -> ScenePlan:
    spec = PACING_SCENE_SPEC[pacing]
    scene_count = spec["scene_count"]
    scene_duration = spec["scene_duration"]

    selected = _select_sections_by_importance(outline.sections, scene_count)

    scenes = []
    for index, section in enumerate(selected):
        narration_beat = (
            section.summary.strip()
            or (section.key_points[0] if section.key_points else "")
            or section.title
        )
        visual_keywords = list(section.key_points)[:5] or [section.title]
        scenes.append(
            Scene(
                index=index,
                title=section.title,
                narration_beat=narration_beat,
                visual_keywords=visual_keywords,
                duration_seconds=scene_duration,
                importance=section.importance,
            )
        )
    return ScenePlan(pacing=pacing, scenes=scenes)
