import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.thinking import idea_generator


class TestBuildIdeaPrompt(unittest.TestCase):
    def test_includes_raw_input(self):
        prompt = idea_generator.build_idea_prompt("Japonya neden güvenli?")
        self.assertIn("Japonya neden güvenli?", prompt)
        self.assertIn("SAME language", prompt)


class TestGenerateIdea(unittest.TestCase):
    @patch("app.thinking.idea_generator.generate_json")
    def test_returns_refined_topic_and_angle(self, mock_generate_json):
        mock_generate_json.return_value = {
            "topic": "Japonya'yı Bu Kadar Güvenli Yapan Nedir?",
            "angle": "Düşük suç oranının arkasındaki dinamikleri ortaya çıkarıyoruz.",
        }
        idea = idea_generator.generate_idea("Japonya neden güvenli?")
        self.assertEqual(idea.topic, "Japonya'yı Bu Kadar Güvenli Yapan Nedir?")
        self.assertEqual(
            idea.angle, "Düşük suç oranının arkasındaki dinamikleri ortaya çıkarıyoruz."
        )

    @patch("app.thinking.idea_generator.generate_json")
    def test_falls_back_to_raw_input_on_llm_failure(self, mock_generate_json):
        mock_generate_json.side_effect = ValueError("mock LLM failure")
        idea = idea_generator.generate_idea("Japonya neden güvenli?")
        self.assertEqual(idea.topic, "Japonya neden güvenli?")
        self.assertEqual(idea.angle, "")

    @patch("app.thinking.idea_generator.generate_json")
    def test_falls_back_to_raw_input_when_llm_returns_empty_topic(self, mock_generate_json):
        mock_generate_json.return_value = {"topic": "", "angle": "irrelevant"}
        idea = idea_generator.generate_idea("Mars colonization")
        self.assertEqual(idea.topic, "Mars colonization")

    def test_empty_input_raises_without_calling_llm(self):
        with patch("app.thinking.idea_generator.generate_json") as mock_generate_json:
            with self.assertRaises(ValueError):
                idea_generator.generate_idea("   ")
            mock_generate_json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
