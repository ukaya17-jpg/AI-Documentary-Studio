import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import TopicCategory
from app.departments.research import intent_analyzer


class TestDetectLanguage(unittest.TestCase):
    def test_detects_turkish_by_characters(self):
        self.assertEqual(intent_analyzer.detect_language("Uzayın Sırları"), "tr")

    def test_defaults_to_english(self):
        self.assertEqual(intent_analyzer.detect_language("Secrets of the Universe"), "en")


class TestHeuristicCategory(unittest.TestCase):
    def test_space_keyword(self):
        self.assertEqual(intent_analyzer._heuristic_category("Journey to Mars"), TopicCategory.space)

    def test_travel_keyword(self):
        self.assertEqual(intent_analyzer._heuristic_category("Best travel destinations"), TopicCategory.travel)

    def test_unknown_falls_back_to_history(self):
        self.assertEqual(intent_analyzer._heuristic_category("xyzzy"), TopicCategory.history)


class TestDetectTopicCategoryWithMockLlm(unittest.TestCase):
    @patch("app.departments.research.intent_analyzer.generate_json")
    def test_uses_llm_result_when_valid(self, mock_generate_json):
        mock_generate_json.return_value = {"category": "psychology"}
        result = intent_analyzer.detect_topic_category("Why do we procrastinate?")
        self.assertEqual(result, TopicCategory.psychology)

    @patch("app.departments.research.intent_analyzer.generate_json")
    def test_falls_back_to_heuristic_on_llm_failure(self, mock_generate_json):
        mock_generate_json.side_effect = ValueError("mock LLM failure")
        result = intent_analyzer.detect_topic_category("The fall of the Roman Empire")
        self.assertEqual(result, TopicCategory.history)

    @patch("app.departments.research.intent_analyzer.generate_json")
    def test_falls_back_to_heuristic_on_invalid_category(self, mock_generate_json):
        mock_generate_json.return_value = {"category": "not-a-real-category"}
        result = intent_analyzer.detect_topic_category("A trip through Japan")
        self.assertEqual(result, TopicCategory.travel)


class TestAnalyzeIntent(unittest.TestCase):
    @patch("app.departments.research.intent_analyzer.generate_json")
    def test_override_wins_over_auto_detect(self, mock_generate_json):
        result = intent_analyzer.analyze_intent(
            "Journey to Mars", language="en", topic_category_override="travel"
        )
        self.assertEqual(result["topic_category"], TopicCategory.travel)
        mock_generate_json.assert_not_called()

    @patch("app.departments.research.intent_analyzer.generate_json")
    def test_auto_detects_category_when_no_override(self, mock_generate_json):
        mock_generate_json.return_value = {"category": "space"}
        result = intent_analyzer.analyze_intent("Journey to Mars", language="en")
        self.assertEqual(result["topic_category"], TopicCategory.space)

    def test_auto_detects_language(self):
        with patch("app.departments.research.intent_analyzer.generate_json", return_value={"category": "history"}):
            result = intent_analyzer.analyze_intent("Roma İmparatorluğu'nun Çöküşü", language="auto")
        self.assertEqual(result["language"], "tr")


if __name__ == "__main__":
    unittest.main()
