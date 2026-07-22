import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.documentary_project import DocumentaryProject
from app.models.outline import Outline, OutlineSection
from app.models.script import Script
from app.models.seo import SeoMetadata
from app.thinking import quality_critic


def _project():
    return DocumentaryProject(
        project_id="p1",
        topic="The Fall of Rome",
        outline=Outline(
            title="The Fall of Rome",
            hook="An empire collapses.",
            sections=[OutlineSection(title="Origins", summary="How Rome rose.")],
            closing="Rome's legacy endures.",
        ),
        script=Script(full_text="Rome was not built in a day. Then it fell."),
        seo=SeoMetadata(title="The Fall of Rome", description="How it happened."),
    )


class TestBuildQualityPrompt(unittest.TestCase):
    def test_includes_topic_script_and_seo(self):
        prompt = quality_critic.build_quality_prompt(_project())
        self.assertIn("The Fall of Rome", prompt)
        self.assertIn("Rome was not built in a day. Then it fell.", prompt)
        self.assertIn("How it happened.", prompt)


class TestEvaluateProject(unittest.TestCase):
    @patch("app.thinking.quality_critic.generate_json")
    def test_computes_overall_score_and_passes(self, mock_generate_json):
        mock_generate_json.return_value = {
            "coherence_score": 4,
            "pacing_fit_score": 5,
            "seo_quality_score": 3,
            "issues": [],
        }
        verdict = quality_critic.evaluate_project(_project())
        self.assertEqual(verdict.overall_score, 4.0)
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.issues, [])

    @patch("app.thinking.quality_critic.generate_json")
    def test_fails_below_threshold(self, mock_generate_json):
        mock_generate_json.return_value = {
            "coherence_score": 2,
            "pacing_fit_score": 3,
            "seo_quality_score": 3,
            "issues": ["Scene 3 references an undefined term."],
        }
        verdict = quality_critic.evaluate_project(_project())
        self.assertAlmostEqual(verdict.overall_score, 2.67, places=2)
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.issues, ["Scene 3 references an undefined term."])

    @patch("app.thinking.quality_critic.generate_json")
    def test_returns_none_on_malformed_response(self, mock_generate_json):
        mock_generate_json.return_value = {"coherence_score": 4}
        verdict = quality_critic.evaluate_project(_project())
        self.assertIsNone(verdict)

    @patch("app.thinking.quality_critic.generate_json")
    def test_returns_none_on_out_of_range_score(self, mock_generate_json):
        mock_generate_json.return_value = {
            "coherence_score": 9,
            "pacing_fit_score": 3,
            "seo_quality_score": 3,
            "issues": [],
        }
        verdict = quality_critic.evaluate_project(_project())
        self.assertIsNone(verdict)

    @patch("app.thinking.quality_critic.generate_json")
    def test_returns_none_on_llm_failure(self, mock_generate_json):
        mock_generate_json.side_effect = ValueError("mock LLM failure")
        verdict = quality_critic.evaluate_project(_project())
        self.assertIsNone(verdict)


if __name__ == "__main__":
    unittest.main()
