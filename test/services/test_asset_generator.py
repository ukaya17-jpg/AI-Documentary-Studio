import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import TopicCategory
from app.models.storyboard import Storyboard, StoryboardShot
from app.departments.production import asset_generator


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

    def test_ai_generated_provider_uses_description_as_prompt_not_search_term(self):
        # AI video path needs a descriptive generative-model prompt, not a
        # stock-search keyword phrase -- search_terms is deliberately unused here.
        storyboard = Storyboard(
            shots=[
                StoryboardShot(
                    scene_index=0,
                    description="a wide shot of ancient ruins at golden hour",
                    shot_type="wide",
                    search_terms=["ancient ruins", "golden hour"],
                )
            ]
        )
        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated")

        self.assertEqual(plan.candidates[0].provider, "ai_generated")
        self.assertEqual(plan.candidates[0].search_term, "")
        self.assertEqual(
            plan.candidates[0].prompt, "wide: a wide shot of ancient ruins at golden hour"
        )

    def test_ai_generated_provider_omits_shot_type_prefix_when_missing(self):
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a lone ruin", shot_type="")]
        )
        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated")

        self.assertEqual(plan.candidates[0].prompt, "a lone ruin")

    def test_ai_generated_prompt_includes_likeness_guard_for_film_highlights(self):
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a dramatic on-set moment")]
        )
        plan = asset_generator.build_asset_plan(
            storyboard, provider="ai_generated", topic_category=TopicCategory.film_highlights
        )

        self.assertIn("a dramatic on-set moment", plan.candidates[0].prompt)
        self.assertIn("Avoid recreating the likeness", plan.candidates[0].prompt)

    def test_ai_generated_prompt_omits_likeness_guard_for_other_categories(self):
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a wide shot of a coral reef")]
        )
        plan = asset_generator.build_asset_plan(
            storyboard, provider="ai_generated", topic_category=TopicCategory.marine
        )

        self.assertNotIn("Avoid recreating the likeness", plan.candidates[0].prompt)


if __name__ == "__main__":
    unittest.main()
