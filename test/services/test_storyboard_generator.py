import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import TopicCategory
from app.models.scene import Scene, ScenePlan
from app.models.script import Script, ScriptLine
from app.departments.creative import storyboard_generator


def _scene_plan():
    return ScenePlan(
        scenes=[
            Scene(index=0, title="Origins", narration_beat="How it began", visual_keywords=["ancient ruins"]),
            Scene(index=1, title="Climax", narration_beat="The turning point", visual_keywords=["battle"]),
        ]
    )


def _script():
    return Script(
        full_text="How it all began.\n\nThe turning point.",
        lines=[
            ScriptLine(scene_index=0, text="How it all began."),
            ScriptLine(scene_index=1, text="The turning point."),
        ],
    )


class TestBuildStoryboardPrompt(unittest.TestCase):
    def test_includes_scene_narration_and_category_guidance(self):
        prompt = storyboard_generator.build_storyboard_prompt(_scene_plan(), _script(), TopicCategory.history)
        self.assertIn("How it all began.", prompt)
        self.assertIn("archival", prompt.lower())


class TestGenerateStoryboard(unittest.TestCase):
    @patch("app.departments.creative.storyboard_generator.generate_json")
    def test_parses_shots_in_scene_order(self, mock_generate_json):
        mock_generate_json.return_value = {
            "shots": [
                {"scene_index": 1, "description": "battle scene", "shot_type": "wide", "search_terms": ["ancient battle"]},
                {"scene_index": 0, "description": "ruins", "shot_type": "close-up", "search_terms": ["ruins closeup"]},
            ]
        }
        storyboard = storyboard_generator.generate_storyboard(_scene_plan(), _script())
        self.assertEqual(storyboard.shots[0].scene_index, 0)
        self.assertEqual(storyboard.shots[0].description, "ruins")
        self.assertEqual(storyboard.shots[1].scene_index, 1)

    @patch("app.departments.creative.storyboard_generator.generate_json")
    def test_falls_back_to_scene_visual_keywords_when_missing(self, mock_generate_json):
        mock_generate_json.return_value = {"shots": [{"scene_index": 0, "description": "ruins", "search_terms": []}]}
        storyboard = storyboard_generator.generate_storyboard(_scene_plan(), _script())
        self.assertEqual(storyboard.shots[0].search_terms, ["ancient ruins"])
        self.assertEqual(storyboard.shots[1].search_terms, ["battle"])

    def test_empty_scene_plan_short_circuits(self):
        with patch("app.departments.creative.storyboard_generator.generate_json") as mock_generate_json:
            storyboard = storyboard_generator.generate_storyboard(ScenePlan(scenes=[]), Script())
            mock_generate_json.assert_not_called()
        self.assertEqual(storyboard.shots, [])


if __name__ == "__main__":
    unittest.main()
