import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import TopicCategory
from app.departments.research import research_planner
from app.models.web_search import WebSearchResult


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

    def test_omits_web_search_grounding_when_none(self):
        prompt = research_planner.build_research_prompt("Mars", TopicCategory.space)
        self.assertNotIn("Verified web source", prompt)

    def test_includes_web_search_grounding_when_present(self):
        result = WebSearchResult(
            heading="Roman Empire",
            abstract="The Roman Empire was the post-Republican period of ancient Rome.",
            source_url="https://en.wikipedia.org/wiki/Roman_Empire",
        )
        prompt = research_planner.build_research_prompt(
            "The Fall of Rome", TopicCategory.history, web_search_result=result
        )
        self.assertIn("Verified web source", prompt)
        self.assertIn("https://en.wikipedia.org/wiki/Roman_Empire", prompt)
        self.assertIn(
            "The Roman Empire was the post-Republican period of ancient Rome.", prompt
        )
        self.assertIn("Do not include key_facts that contradict it", prompt)


class TestGenerateResearchPlan(unittest.TestCase):
    @patch("app.departments.research.research_planner.web_search.search_web", return_value=None)
    @patch("app.departments.research.research_planner.generate_json")
    def test_parses_full_valid_response(self, mock_generate_json, mock_search_web):
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
        self.assertEqual(plan.source_snippet, "")
        self.assertEqual(plan.source_url, "")

    @patch("app.departments.research.research_planner.web_search.search_web", return_value=None)
    @patch("app.departments.research.research_planner.generate_json")
    def test_tolerates_string_only_questions(self, mock_generate_json, mock_search_web):
        mock_generate_json.return_value = {
            "key_questions": ["Why did Rome fall?"],
            "key_facts": [],
            "angles": [],
        }
        plan = research_planner.generate_research_plan("The Fall of Rome")
        self.assertEqual(plan.key_questions[0].question, "Why did Rome fall?")
        self.assertEqual(plan.key_questions[0].rationale, "")

    @patch("app.departments.research.research_planner.web_search.search_web", return_value=None)
    @patch("app.departments.research.research_planner.generate_json")
    def test_drops_empty_questions(self, mock_generate_json, mock_search_web):
        mock_generate_json.return_value = {
            "key_questions": [{"question": "", "rationale": "n/a"}, ""],
            "key_facts": [],
            "angles": [],
        }
        plan = research_planner.generate_research_plan("Topic")
        self.assertEqual(plan.key_questions, [])

    @patch("app.departments.research.research_planner.web_search.search_web")
    @patch("app.departments.research.research_planner.generate_json")
    def test_stores_source_snippet_and_url_when_search_finds_a_result(
        self, mock_generate_json, mock_search_web
    ):
        mock_search_web.return_value = WebSearchResult(
            heading="Roman Empire",
            abstract="The Roman Empire was the post-Republican period of ancient Rome.",
            source_url="https://en.wikipedia.org/wiki/Roman_Empire",
        )
        mock_generate_json.return_value = {"key_questions": [], "key_facts": [], "angles": []}

        plan = research_planner.generate_research_plan("The Fall of Rome", TopicCategory.history)

        mock_search_web.assert_called_once_with("The Fall of Rome")
        self.assertEqual(
            plan.source_snippet,
            "The Roman Empire was the post-Republican period of ancient Rome.",
        )
        self.assertEqual(plan.source_url, "https://en.wikipedia.org/wiki/Roman_Empire")
        # The prompt actually sent to the LLM must carry the grounding text.
        prompt_arg = mock_generate_json.call_args[0][0]
        self.assertIn("Verified web source", prompt_arg)


if __name__ == "__main__":
    unittest.main()
