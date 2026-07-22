import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.departments.growth import seo_generator
from app.models.scene import Scene, ScenePlan
from app.models.script import Script


def _scene_plan():
    return ScenePlan(
        scenes=[
            Scene(index=0, title="Origins", duration_seconds=5.0),
            Scene(index=1, title="Decline", duration_seconds=65.0),
            Scene(index=2, title="Fall", duration_seconds=8.0),
        ]
    )


class TestGenerateChapters(unittest.TestCase):
    def test_computes_cumulative_mm_ss_markers(self):
        chapters = seo_generator.generate_chapters(_scene_plan())
        self.assertEqual(chapters, ["0:00 Origins", "0:05 Decline", "1:10 Fall"])

    def test_returns_empty_list_for_none(self):
        self.assertEqual(seo_generator.generate_chapters(None), [])

    def test_returns_empty_list_for_empty_scene_plan(self):
        self.assertEqual(seo_generator.generate_chapters(ScenePlan(scenes=[])), [])


class TestGenerateEngagementMetadata(unittest.TestCase):
    @patch("app.departments.growth.seo_generator.generate_json")
    def test_returns_parsed_fields(self, mock_generate_json):
        mock_generate_json.return_value = {
            "end_screen_suggestion": "Ask viewers to subscribe for more history content.",
            "pinned_comment": "What do you think caused Rome's fall the most?",
        }
        result = seo_generator.generate_engagement_metadata(
            "The Fall of Rome", Script(full_text="Rome fell.")
        )
        self.assertEqual(
            result["end_screen_suggestion"],
            "Ask viewers to subscribe for more history content.",
        )
        self.assertEqual(
            result["pinned_comment"], "What do you think caused Rome's fall the most?"
        )

    @patch("app.departments.growth.seo_generator.generate_json")
    def test_returns_empty_strings_on_failure(self, mock_generate_json):
        mock_generate_json.side_effect = ValueError("mock LLM failure")
        result = seo_generator.generate_engagement_metadata(
            "The Fall of Rome", Script(full_text="Rome fell.")
        )
        self.assertEqual(result, {"end_screen_suggestion": "", "pinned_comment": ""})


class TestGenerateSeoMetadata(unittest.TestCase):
    @patch("app.departments.growth.seo_generator.generate_json")
    @patch("app.departments.growth.seo_generator.llm.generate_social_metadata")
    def test_maps_social_metadata_result_to_seo_metadata(
        self, mock_generate_social_metadata, mock_generate_json
    ):
        mock_generate_social_metadata.return_value = {
            "title": "The Fall of Rome",
            "caption": "How the mightiest empire in history collapsed.",
            "hashtags": ["#history", "#rome"],
        }
        mock_generate_json.return_value = {
            "end_screen_suggestion": "Subscribe for more.",
            "pinned_comment": "What do you think?",
        }
        script = Script(full_text="Rome fell in 476 AD.")
        seo = seo_generator.generate_seo_metadata(
            "The Fall of Rome", script, language="en", scene_plan=_scene_plan()
        )

        self.assertEqual(seo.title, "The Fall of Rome")
        self.assertEqual(seo.description, "How the mightiest empire in history collapsed.")
        self.assertEqual(seo.hashtags, ["#history", "#rome"])
        self.assertEqual(seo.chapters, ["0:00 Origins", "0:05 Decline", "1:10 Fall"])
        self.assertEqual(seo.end_screen_suggestion, "Subscribe for more.")
        self.assertEqual(seo.pinned_comment, "What do you think?")
        mock_generate_social_metadata.assert_called_once_with(
            video_subject="The Fall of Rome",
            video_script="Rome fell in 476 AD.",
            language="en",
            platform="youtube_shorts",
        )

    @patch("app.departments.growth.seo_generator.generate_json")
    @patch("app.departments.growth.seo_generator.llm.generate_social_metadata")
    def test_empty_chapters_when_no_scene_plan_given(
        self, mock_generate_social_metadata, mock_generate_json
    ):
        mock_generate_social_metadata.return_value = {
            "title": "T", "caption": "C", "hashtags": []
        }
        mock_generate_json.return_value = {}
        seo = seo_generator.generate_seo_metadata("T", Script(full_text="text"))
        self.assertEqual(seo.chapters, [])


if __name__ == "__main__":
    unittest.main()
