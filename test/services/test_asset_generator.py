import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.storyboard import Storyboard, StoryboardShot
from app.services import asset_generator


class TestBuildAssetPlan(unittest.TestCase):
    def test_uses_first_search_term_per_shot(self):
        storyboard = Storyboard(
            shots=[
                StoryboardShot(scene_index=0, description="ruins", search_terms=["ancient ruins", "rome"]),
                StoryboardShot(scene_index=1, description="battle", search_terms=["battle field"]),
            ]
        )
        plan = asset_generator.build_asset_plan(storyboard)
        self.assertEqual(len(plan.candidates), 2)
        self.assertEqual(plan.candidates[0].search_term, "ancient ruins")
        self.assertEqual(plan.candidates[0].scene_index, 0)
        self.assertEqual(plan.candidates[1].search_term, "battle field")

    def test_falls_back_to_description_when_no_search_terms(self):
        storyboard = Storyboard(shots=[StoryboardShot(scene_index=0, description="a lone ruin", search_terms=[])])
        plan = asset_generator.build_asset_plan(storyboard)
        self.assertEqual(plan.candidates[0].search_term, "a lone ruin")

    def test_uses_provider_override(self):
        storyboard = Storyboard(shots=[StoryboardShot(scene_index=0, search_terms=["x"])])
        plan = asset_generator.build_asset_plan(storyboard, provider="pixabay")
        self.assertEqual(plan.candidates[0].provider, "pixabay")

    def test_empty_storyboard_yields_empty_plan(self):
        plan = asset_generator.build_asset_plan(Storyboard(shots=[]))
        self.assertEqual(plan.candidates, [])


if __name__ == "__main__":
    unittest.main()
