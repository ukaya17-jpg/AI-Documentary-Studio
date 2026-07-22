import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import TopicCategory
from app.models.research_plan import ResearchPlan, ResearchQuestion
from app.services import outline_generator


class TestBuildOutlinePrompt(unittest.TestCase):
    def test_includes_style_guidance_and_topic(self):
        prompt = outline_generator.build_outline_prompt("The Fall of Rome", topic_category=TopicCategory.history)
        self.assertIn("The Fall of Rome", prompt)
        self.assertIn("chronological", prompt.lower())

    def test_includes_research_brief_when_present(self):
        plan = ResearchPlan(
            topic="Mars",
            key_questions=[ResearchQuestion(question="Is there water on Mars?")],
            key_facts=["Mars has two moons."],
            angles=["Mars as humanity's next frontier."],
        )
        prompt = outline_generator.build_outline_prompt("Mars", research_plan=plan, topic_category=TopicCategory.space)
        self.assertIn("Mars has two moons.", prompt)
        self.assertIn("Is there water on Mars?", prompt)
        self.assertIn("Mars as humanity's next frontier.", prompt)

    def test_omits_research_brief_when_absent(self):
        prompt = outline_generator.build_outline_prompt("Mars", topic_category=TopicCategory.space)
        self.assertNotIn("Research brief", prompt)


class TestGenerateOutline(unittest.TestCase):
    @patch("app.services.outline_generator.generate_json")
    def test_parses_full_valid_response(self, mock_generate_json):
        mock_generate_json.return_value = {
            "title": "The Fall of Rome",
            "hook": "In 476 AD, an empire that ruled the known world collapsed.",
            "sections": [
                {"title": "Origins", "summary": "How Rome rose.", "key_points": ["Founded 753 BC"], "importance": 4},
                {"title": "Decline", "summary": "The slow fall.", "key_points": [], "importance": 5},
            ],
            "closing": "Rome's legacy endures today.",
        }
        outline = outline_generator.generate_outline("The Fall of Rome", topic_category=TopicCategory.history)
        self.assertEqual(outline.title, "The Fall of Rome")
        self.assertEqual(len(outline.sections), 2)
        self.assertEqual(outline.sections[1].importance, 5)

    @patch("app.services.outline_generator.generate_json")
    def test_falls_back_to_topic_when_title_missing(self, mock_generate_json):
        mock_generate_json.return_value = {"sections": []}
        outline = outline_generator.generate_outline("Mars")
        self.assertEqual(outline.title, "Mars")

    @patch("app.services.outline_generator.generate_json")
    def test_clamps_out_of_range_importance(self, mock_generate_json):
        mock_generate_json.return_value = {
            "title": "T",
            "sections": [{"title": "A", "importance": 99}, {"title": "B", "importance": -3}],
        }
        outline = outline_generator.generate_outline("T")
        self.assertEqual(outline.sections[0].importance, 5)
        self.assertEqual(outline.sections[1].importance, 1)

    @patch("app.services.outline_generator.generate_json")
    def test_skips_sections_without_title(self, mock_generate_json):
        mock_generate_json.return_value = {"title": "T", "sections": [{"summary": "no title"}]}
        outline = outline_generator.generate_outline("T")
        self.assertEqual(outline.sections, [])


if __name__ == "__main__":
    unittest.main()
