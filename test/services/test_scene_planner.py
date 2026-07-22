import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import Pacing
from app.models.outline import Outline, OutlineSection
from app.services import scene_planner


def _outline_with_sections(importances: list[int]) -> Outline:
    return Outline(
        title="T",
        sections=[
            OutlineSection(title=f"Section {i}", summary=f"Summary {i}", importance=imp)
            for i, imp in enumerate(importances)
        ],
    )


class TestPlanScenes(unittest.TestCase):
    def test_short_pacing_yields_four_scenes_of_five_seconds(self):
        outline = _outline_with_sections([1, 2, 3, 4, 5, 2])
        plan = scene_planner.plan_scenes(outline, Pacing.short)
        self.assertEqual(len(plan.scenes), 4)
        self.assertTrue(all(s.duration_seconds == 5.0 for s in plan.scenes))

    def test_long_pacing_yields_seven_scenes_of_eight_seconds(self):
        outline = _outline_with_sections([1, 2, 3, 4, 5, 1, 2, 3, 4, 5])
        plan = scene_planner.plan_scenes(outline, Pacing.long)
        self.assertEqual(len(plan.scenes), 7)
        self.assertTrue(all(s.duration_seconds == 8.0 for s in plan.scenes))

    def test_keeps_highest_importance_sections(self):
        outline = _outline_with_sections([1, 5, 2, 4, 1, 3])
        plan = scene_planner.plan_scenes(outline, Pacing.short)
        kept_importances = sorted(s.importance for s in plan.scenes)
        self.assertEqual(kept_importances, [2, 3, 4, 5])

    def test_preserves_original_narrative_order(self):
        outline = _outline_with_sections([5, 1, 4, 1, 3, 2])
        plan = scene_planner.plan_scenes(outline, Pacing.short)
        titles = [s.title for s in plan.scenes]
        self.assertEqual(titles, ["Section 0", "Section 2", "Section 4", "Section 5"])

    def test_uses_fewer_scenes_when_outline_is_shorter_than_budget(self):
        outline = _outline_with_sections([3, 4])
        plan = scene_planner.plan_scenes(outline, Pacing.short)
        self.assertEqual(len(plan.scenes), 2)

    def test_narration_beat_falls_back_to_key_point_then_title(self):
        outline = Outline(
            title="T",
            sections=[
                OutlineSection(title="A", summary="", key_points=["kp1"], importance=5),
                OutlineSection(title="B", summary="", key_points=[], importance=5),
            ],
        )
        plan = scene_planner.plan_scenes(outline, Pacing.short)
        self.assertEqual(plan.scenes[0].narration_beat, "kp1")
        self.assertEqual(plan.scenes[1].narration_beat, "B")

    def test_scene_plan_total_duration_matches_pacing_budget(self):
        outline = _outline_with_sections([1, 2, 3, 4])
        plan = scene_planner.plan_scenes(outline, Pacing.short)
        self.assertEqual(plan.total_duration, 20.0)


if __name__ == "__main__":
    unittest.main()
