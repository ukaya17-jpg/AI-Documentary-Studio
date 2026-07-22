import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import TopicCategory
from app.departments.research import research_planner


class TestBuildResearchPrompt(unittest.TestCase):
    def test_includes_topic_and_style_guidance(self):
        prompt = research_planner.build_research_prompt(
            "The Fall of Rome", TopicCategory.history, language="en"
        )
        self.assertIn("The Fall of Rome", prompt)
        self.assertIn("chronological", prompt.lower())
        self.assertIn("Respond in language: en", prompt)

    def test_omits_language_line_for_auto(self):
        prompt = research_planner.build_research_prompt("Mars", TopicCategory.space, language="auto")
        self.assertNotIn("Respond in language", prompt)


class TestGenerateResearchPlan(unittest.TestCase):
    @patch("app.departments.research.research_planner.generate_json")
    def test_parses_full_valid_response(self, mock_generate_json):
        mock_generate_json.return_value = {
            "key_questions": [
                {"question": "Why did Rome fall?", "rationale": "central mystery"},
            ],
            "key_facts": ["Rome fell in 476 AD."],
            "angles": ["Decline as a slow process, not a single event."],
        }
        plan = research_planner.generate_research_plan("The Fall of Rome", TopicCategory.history)
        self.assertEqual(plan.topic, "The Fall of Rome")
        self.assertEqual(len(plan.key_questions), 1)
        self.assertEqual(plan.key_questions[0].question, "Why did Rome fall?")
        self.assertEqual(plan.key_facts, ["Rome fell in 476 AD."])
        self.assertEqual(plan.angles, ["Decline as a slow process, not a single event."])

    @patch("app.departments.research.research_planner.generate_json")
    def test_tolerates_string_only_questions(self, mock_generate_json):
        mock_generate_json.return_value = {
            "key_questions": ["Why did Rome fall?"],
            "key_facts": [],
            "angles": [],
        }
        plan = research_planner.generate_research_plan("The Fall of Rome")
        self.assertEqual(plan.key_questions[0].question, "Why did Rome fall?")
        self.assertEqual(plan.key_questions[0].rationale, "")

    @patch("app.departments.research.research_planner.generate_json")
    def test_drops_empty_questions(self, mock_generate_json):
        mock_generate_json.return_value = {
            "key_questions": [{"question": "", "rationale": "n/a"}, ""],
            "key_facts": [],
            "angles": [],
        }
        plan = research_planner.generate_research_plan("Topic")
        self.assertEqual(plan.key_questions, [])


if __name__ == "__main__":
    unittest.main()
