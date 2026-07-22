import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.scene import Scene, ScenePlan
from app.departments.creative import script_generator


def _scene_plan():
    return ScenePlan(
        scenes=[
            Scene(index=0, title="Origins", narration_beat="How it began", duration_seconds=5.0),
            Scene(index=1, title="Climax", narration_beat="The turning point", duration_seconds=5.0),
        ]
    )


class TestBuildScriptPrompt(unittest.TestCase):
    def test_includes_topic_and_scene_word_targets(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "The Fall of Rome")
        self.assertIn("The Fall of Rome", prompt)
        self.assertIn("scene 0", prompt)
        self.assertIn("scene 1", prompt)
        self.assertIn("words", prompt)

    def test_custom_system_prompt_replaces_default(self):
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", custom_system_prompt="Custom voice instructions."
        )
        self.assertIn("Custom voice instructions.", prompt)
        self.assertNotIn(script_generator.DEFAULT_SCRIPT_SYSTEM_PROMPT, prompt)


class TestGenerateScript(unittest.TestCase):
    @patch("app.departments.creative.script_generator.generate_json")
    def test_parses_lines_in_scene_order(self, mock_generate_json):
        mock_generate_json.return_value = {
            "lines": [
                {"scene_index": 1, "text": "Everything changed in an instant."},
                {"scene_index": 0, "text": "It all started long ago."},
            ]
        }
        script = script_generator.generate_script(_scene_plan(), "Topic")
        self.assertEqual(script.lines[0].text, "It all started long ago.")
        self.assertEqual(script.lines[1].text, "Everything changed in an instant.")
        self.assertIn("It all started long ago.", script.full_text)

    @patch("app.departments.creative.script_generator.generate_json")
    def test_falls_back_to_narration_beat_for_missing_scene(self, mock_generate_json):
        mock_generate_json.return_value = {"lines": [{"scene_index": 0, "text": "Only scene 0 written."}]}
        script = script_generator.generate_script(_scene_plan(), "Topic")
        self.assertEqual(script.lines[1].text, "The turning point")

    def test_empty_scene_plan_short_circuits_without_llm_call(self):
        with patch("app.departments.creative.script_generator.generate_json") as mock_generate_json:
            script = script_generator.generate_script(ScenePlan(scenes=[]), "Topic")
            mock_generate_json.assert_not_called()
        self.assertEqual(script.full_text, "")
        self.assertEqual(script.lines, [])


if __name__ == "__main__":
    unittest.main()
