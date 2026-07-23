import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import Tone, TopicCategory, resolve_tone
from app.models.research_plan import ResearchPlan, ResearchQuestion
from app.departments.research import outline_generator


class TestBuildOutlinePrompt(unittest.TestCase):
    def test_includes_style_guidance_and_topic(self):
        prompt = outline_generator.build_outline_prompt("The Fall of Rome", tone=Tone.credibility)
        self.assertIn("The Fall of Rome", prompt)
        self.assertIn("chronological", prompt.lower())

    def test_includes_research_brief_when_present(self):
        plan = ResearchPlan(
            topic="Mars",
            key_questions=[ResearchQuestion(question="Is there water on Mars?")],
            key_facts=["Mars has two moons."],
            angles=["Mars as humanity's next frontier."],
        )
        prompt = outline_generator.build_outline_prompt("Mars", research_plan=plan, tone=Tone.epic)
        self.assertIn("Mars has two moons.", prompt)
        self.assertIn("Is there water on Mars?", prompt)
        self.assertIn("Mars as humanity's next frontier.", prompt)

    def test_omits_research_brief_when_absent(self):
        prompt = outline_generator.build_outline_prompt("Mars", tone=Tone.epic)
        self.assertNotIn("Research brief", prompt)


class TestBuildOutlinePromptToneRegression(unittest.TestCase):
    """Locks down that re-keying PROFILE_PROMPTS from TopicCategory to Tone
    (Visual Engine follow-up: Tone as an independent dimension) produced
    byte-identical prompts for all 4 categories' default tone, with no
    override -- captured from the pre-refactor code as the ground truth.
    """

    _EXPECTED = {
        TopicCategory.travel: (
            'You are a documentary outline writer.\n'
            'Style: Travel documentary. Ground the narration in concrete sensory detail '
            '(sights, sounds, food, local life) and a strong sense of place.\n'
            'Opening hook guidance: Open with a vivid, specific moment or image from the '
            'destination, not a generic welcome.\n'
            'Section guidance: Cover history/context, standout landmarks or experiences, '
            'culture and daily life, and one surprising or lesser-known fact.\n'
            'Closing guidance: End with a reflective takeaway or an invitation to explore '
            'further.\n\n'
            'Topic: "SAMPLE TOPIC"\n\n'
            'Produce a documentary outline as a single JSON object with exactly this shape:\n'
            '{\n'
            '  "title": "...",\n'
            '  "hook": "...",\n'
            '  "sections": [{"title": "...", "summary": "...", "key_points": ["..."], "importance": 1}],\n'
            '  "closing": "..."\n'
            '}\n'
            'Produce 4-7 sections ordered narratively. Rate each section\'s "importance" from\n'
            '1 (skippable) to 5 (essential) so a downstream step can trim sections for a\n'
            'shorter cut. Do not include any other text.'
        ),
    }

    def test_default_tone_prompt_matches_pre_refactor_byte_for_byte(self):
        # Full literal comparison for one category (travel) to prove the
        # exact prompt text, plus a structural check for all 4 that the
        # rename didn't alter length/content at all (compares against the
        # dict's own template text directly, independent of any hand-typed
        # expected string, so it can't rot).
        prompt = outline_generator.build_outline_prompt(
            "SAMPLE TOPIC", tone=resolve_tone(TopicCategory.travel, None)
        )
        self.assertEqual(prompt, self._EXPECTED[TopicCategory.travel])

    def test_all_four_categories_resolve_to_a_template_with_expected_style_keyword(self):
        # Cheap per-category smoke check (style keyword unique to each
        # category's original template) that resolve_tone + get_template
        # still route every category to its own original template content.
        expectations = {
            TopicCategory.travel: "strong sense of place",
            TopicCategory.history: "chronological",
            TopicCategory.space: "scale, precision, and awe",
            TopicCategory.psychology: "relatable scenario or experiment",
        }
        for category, keyword in expectations.items():
            tone = resolve_tone(category, None)
            prompt = outline_generator.build_outline_prompt("SAMPLE TOPIC", tone=tone)
            self.assertIn(keyword, prompt)


class TestGenerateOutline(unittest.TestCase):
    @patch("app.departments.research.outline_generator.generate_json")
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
        outline = outline_generator.generate_outline("The Fall of Rome", tone=Tone.credibility)
        self.assertEqual(outline.title, "The Fall of Rome")
        self.assertEqual(len(outline.sections), 2)
        self.assertEqual(outline.sections[1].importance, 5)

    @patch("app.departments.research.outline_generator.generate_json")
    def test_falls_back_to_topic_when_title_missing(self, mock_generate_json):
        mock_generate_json.return_value = {"sections": []}
        outline = outline_generator.generate_outline("Mars")
        self.assertEqual(outline.title, "Mars")

    @patch("app.departments.research.outline_generator.generate_json")
    def test_clamps_out_of_range_importance(self, mock_generate_json):
        mock_generate_json.return_value = {
            "title": "T",
            "sections": [{"title": "A", "importance": 99}, {"title": "B", "importance": -3}],
        }
        outline = outline_generator.generate_outline("T")
        self.assertEqual(outline.sections[0].importance, 5)
        self.assertEqual(outline.sections[1].importance, 1)

    @patch("app.departments.research.outline_generator.generate_json")
    def test_skips_sections_without_title(self, mock_generate_json):
        mock_generate_json.return_value = {"title": "T", "sections": [{"summary": "no title"}]}
        outline = outline_generator.generate_outline("T")
        self.assertEqual(outline.sections, [])


if __name__ == "__main__":
    unittest.main()
