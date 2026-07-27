import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import Format, Tone
from app.models.outline import Outline
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

    def test_custom_system_prompt_is_additive_not_replacing(self):
        # Kullanıcı bulgusu: eskiden custom_system_prompt DEFAULT_SCRIPT_
        # SYSTEM_PROMPT'un yerine geçiyordu -- zararsız görünen bir stil
        # isteği bile "no markdown, no scene labels" korumasını sessizce
        # siliyordu. custom_requirements ile tutarlı olacak şekilde artık
        # additive: temel talimat HER ZAMAN kalıyor.
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", custom_system_prompt="Custom voice instructions."
        )
        self.assertIn("Custom voice instructions.", prompt)
        self.assertIn(script_generator.DEFAULT_SCRIPT_SYSTEM_PROMPT, prompt)

    def test_blank_custom_system_prompt_adds_no_extra_block(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic", custom_system_prompt="   ")
        self.assertNotIn("Additional style guidance:", prompt)

    def test_omitting_custom_system_prompt_leaves_base_prompt_unchanged(self):
        without = script_generator.build_script_prompt(_scene_plan(), "Topic")
        self.assertTrue(without.startswith(script_generator.DEFAULT_SCRIPT_SYSTEM_PROMPT))
        self.assertNotIn("Additional style guidance:", without)

    def test_omits_hook_and_callback_without_outline(self):
        # Retention is independent of the outline and still applies to a
        # multi-scene plan, but Hook/Callback require outline.hook/closing.
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic")
        self.assertNotIn("Hook:", prompt)
        self.assertNotIn("Callback:", prompt)

    def test_omits_story_craft_block_entirely_for_single_scene_without_outline(self):
        single_scene_plan = ScenePlan(
            scenes=[Scene(index=0, title="Only", narration_beat="The whole story", duration_seconds=5.0)]
        )
        prompt = script_generator.build_script_prompt(single_scene_plan, "Topic")
        self.assertNotIn("Story craft requirements", prompt)

    def test_includes_hook_and_callback_when_outline_present(self):
        outline = Outline(
            title="The Fall of Rome",
            hook="An empire that ruled the known world collapsed.",
            closing="Rome's legacy endures today.",
        )
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic", outline=outline)
        self.assertIn("Story craft requirements", prompt)
        self.assertIn("Hook:", prompt)
        self.assertIn("An empire that ruled the known world collapsed.", prompt)
        self.assertIn("Callback:", prompt)
        self.assertIn("Rome's legacy endures today.", prompt)

    def test_includes_retention_instruction_for_multi_scene_plan(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic")
        self.assertIn("Retention:", prompt)

    def test_omits_retention_instruction_for_single_scene_plan(self):
        single_scene_plan = ScenePlan(
            scenes=[Scene(index=0, title="Only", narration_beat="The whole story", duration_seconds=5.0)]
        )
        prompt = script_generator.build_script_prompt(single_scene_plan, "Topic")
        self.assertNotIn("Retention:", prompt)

    def test_omits_hook_instruction_when_outline_hook_is_blank(self):
        outline = Outline(title="T", hook="", closing="Real closing.")
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic", outline=outline)
        self.assertNotIn("Hook:", prompt)
        self.assertIn("Callback:", prompt)


class TestBuildScriptPromptTone(unittest.TestCase):
    """script_generator previously took no topic_category/tone at all -- this
    is new wiring (Tone as an independent dimension), not a re-keyed old
    behavior, so there's no old text to stay byte-identical to. The only
    regression contract here is: omitting tone must leave the prompt exactly
    as it was before Tone existed.
    """

    def test_omitting_tone_adds_no_voice_line(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic")
        self.assertNotIn("Voice:", prompt)

    def test_tone_adds_a_voice_line_with_matching_guidance(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic", tone=Tone.epic)
        self.assertIn("Voice:", prompt)
        self.assertIn(script_generator.TONE_VOICE_GUIDANCE[Tone.epic], prompt)

    def test_different_tones_produce_different_voice_text(self):
        cinematic_prompt = script_generator.build_script_prompt(_scene_plan(), "Topic", tone=Tone.cinematic)
        scientific_prompt = script_generator.build_script_prompt(_scene_plan(), "Topic", tone=Tone.scientific)
        self.assertNotEqual(cinematic_prompt, scientific_prompt)
        self.assertIn(script_generator.TONE_VOICE_GUIDANCE[Tone.cinematic], cinematic_prompt)
        self.assertIn(script_generator.TONE_VOICE_GUIDANCE[Tone.scientific], scientific_prompt)

    def test_all_tones_have_voice_guidance(self):
        for tone in Tone:
            self.assertIn(tone, script_generator.TONE_VOICE_GUIDANCE)


class TestBuildScriptPromptFormat(unittest.TestCase):
    """Format is new wiring too (like tone was), independent of it: a Format
    line and a Voice line can both be present, and omitting format must
    leave the prompt exactly as it was before Format existed -- including
    with a tone set, since the two are orthogonal.
    """

    def test_omitting_format_adds_no_format_line(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic")
        self.assertNotIn("Format:", prompt)

    def test_omitting_format_adds_no_format_line_even_with_tone_set(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic", tone=Tone.epic)
        self.assertNotIn("Format:", prompt)

    def test_educational_format_adds_a_format_line_with_matching_guidance(self):
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", format=Format.educational
        )
        self.assertIn("Format:", prompt)
        self.assertIn(script_generator.FORMAT_GUIDANCE[Format.educational], prompt)

    def test_educational_format_guidance_forbids_a_literal_takeaway_label(self):
        # OTONOM KARAR (gece oturumu, GÖREV A): a real production run showed
        # the LLM taking the word "takeaway" in the old instruction literally,
        # prefixing every scene with "Takeaway:" as spoken narration -- this
        # locks in the reworded instruction that explicitly forbids that.
        guidance = script_generator.FORMAT_GUIDANCE[Format.educational]
        self.assertIn("never write a literal label", guidance)

    def test_educational_format_and_tone_coexist(self):
        # Tone shapes voice, Format shapes structure -- both lines should be
        # present together, neither one crowding out the other.
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", tone=Tone.epic, format=Format.educational
        )
        self.assertIn("Voice:", prompt)
        self.assertIn("Format:", prompt)
        self.assertIn(script_generator.TONE_VOICE_GUIDANCE[Tone.epic], prompt)
        self.assertIn(script_generator.FORMAT_GUIDANCE[Format.educational], prompt)

    def test_corporate_format_adds_a_format_line_with_matching_guidance(self):
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", format=Format.corporate
        )
        self.assertIn("Format:", prompt)
        self.assertIn(script_generator.FORMAT_GUIDANCE[Format.corporate], prompt)

    def test_corporate_format_and_tone_coexist(self):
        # Same contract as educational+tone: Corporate is a Format, so it
        # must be able to sit alongside any Tone without either line
        # crowding out the other.
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", tone=Tone.credibility, format=Format.corporate
        )
        self.assertIn("Voice:", prompt)
        self.assertIn("Format:", prompt)
        self.assertIn(script_generator.TONE_VOICE_GUIDANCE[Tone.credibility], prompt)
        self.assertIn(script_generator.FORMAT_GUIDANCE[Format.corporate], prompt)

    def test_educational_and_corporate_produce_different_format_text(self):
        educational_prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", format=Format.educational
        )
        corporate_prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", format=Format.corporate
        )
        self.assertNotEqual(educational_prompt, corporate_prompt)
        self.assertNotIn(script_generator.FORMAT_GUIDANCE[Format.corporate], educational_prompt)
        self.assertNotIn(script_generator.FORMAT_GUIDANCE[Format.educational], corporate_prompt)

    def test_all_formats_have_guidance(self):
        for fmt in Format:
            self.assertIn(fmt, script_generator.FORMAT_GUIDANCE)


class TestGrowthGuidance(unittest.TestCase):
    """GÖREV 3 (TAM OTONOMİ, kullanıcı onaylı): platform büyüme ilkeleri --
    Tone/Format gibi kullanıcı seçimi DEĞİL, her zaman açık, kapatılamaz.
    """

    def test_present_unconditionally_even_with_no_tone_format_or_outline(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic")
        self.assertIn("Growth requirements:", prompt)
        self.assertIn("Opening:", prompt)
        self.assertIn("Advertiser-safe:", prompt)
        self.assertIn("Series feel:", prompt)

    def test_present_for_a_single_scene_plan_too(self):
        # Story craft's Retention bullet is skipped for a single scene, but
        # growth guidance is unconditional -- must still appear.
        single_scene_plan = ScenePlan(
            scenes=[Scene(index=0, title="Only", narration_beat="The whole story", duration_seconds=5.0)]
        )
        prompt = script_generator.build_script_prompt(single_scene_plan, "Topic")
        self.assertIn("Growth requirements:", prompt)

    def test_includes_closing_nudge_and_engagement_question_by_default(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic")
        self.assertIn("Closing nudge:", prompt)
        self.assertIn("Engagement:", prompt)

    def test_suppresses_closing_nudge_and_engagement_for_corporate_format(self):
        # Format.corporate explicitly asks for a neutral, non-promotional,
        # third-person voice -- a subscribe-style nudge or a direct
        # engagement question would contradict that.
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", format=Format.corporate
        )
        self.assertNotIn("Closing nudge:", prompt)
        self.assertNotIn("Engagement:", prompt)
        # The rest of growth guidance still applies -- corporate isn't exempt
        # from the ad-safe/opening/series-feel requirements.
        self.assertIn("Opening:", prompt)
        self.assertIn("Advertiser-safe:", prompt)
        self.assertIn("Series feel:", prompt)

    def test_keeps_closing_nudge_and_engagement_for_educational_format(self):
        # Only corporate is exempted -- educational (or no format at all)
        # keeps the full growth block.
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", format=Format.educational
        )
        self.assertIn("Closing nudge:", prompt)
        self.assertIn("Engagement:", prompt)

    def test_retention_instruction_now_asks_for_regular_new_detail(self):
        # Reinforces (rather than duplicating with a separate, potentially
        # contradictory instruction) the existing per-scene Retention rule.
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic")
        self.assertIn("a new concrete detail or turn should surface", prompt)


class TestCustomRequirements(unittest.TestCase):
    """GÖREV F (kullanıcı onaylı): kullanıcının kendi ek talimatları --
    otomatik büyüme ilkelerinin (Growth requirements) YERİNE değil, onun
    hemen ardına ek bir blok olarak eklenir, ikisi çakışmaz.
    """

    def test_omitting_custom_requirements_adds_no_extra_block(self):
        prompt = script_generator.build_script_prompt(_scene_plan(), "Topic")
        self.assertNotIn("Additional requirements:", prompt)

    def test_blank_custom_requirements_adds_no_extra_block(self):
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", custom_requirements="   "
        )
        self.assertNotIn("Additional requirements:", prompt)

    def test_custom_requirements_appear_after_growth_requirements(self):
        prompt = script_generator.build_script_prompt(
            _scene_plan(), "Topic", custom_requirements="Always mention the year."
        )
        self.assertIn("Additional requirements:", prompt)
        self.assertIn("Always mention the year.", prompt)
        self.assertLess(
            prompt.index("Growth requirements:"),
            prompt.index("Additional requirements:"),
        )

    def test_custom_requirements_coexist_with_growth_requirements_unmodified(self):
        # The growth block itself must stay byte-identical -- custom
        # requirements are additive, not a replacement.
        without = script_generator.build_script_prompt(_scene_plan(), "Topic")
        with_custom = script_generator.build_script_prompt(
            _scene_plan(), "Topic", custom_requirements="Mention the year."
        )
        growth_block = without[
            without.index("Growth requirements:") : without.index(
                "Respond with a single JSON object"
            )
        ]
        self.assertIn(growth_block.strip(), with_custom)


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

    @patch("app.departments.creative.script_generator.generate_json")
    def test_passes_outline_through_to_the_prompt(self, mock_generate_json):
        mock_generate_json.return_value = {"lines": []}
        outline = Outline(title="T", hook="Real hook line.", closing="Real closing line.")

        script_generator.generate_script(_scene_plan(), "Topic", outline=outline)

        prompt_arg = mock_generate_json.call_args[0][0]
        self.assertIn("Real hook line.", prompt_arg)
        self.assertIn("Real closing line.", prompt_arg)

    @patch("app.departments.creative.script_generator.generate_json")
    def test_passes_tone_through_to_the_prompt(self, mock_generate_json):
        mock_generate_json.return_value = {"lines": []}

        script_generator.generate_script(_scene_plan(), "Topic", tone=Tone.scientific)

        prompt_arg = mock_generate_json.call_args[0][0]
        self.assertIn(script_generator.TONE_VOICE_GUIDANCE[Tone.scientific], prompt_arg)

    @patch("app.departments.creative.script_generator.generate_json")
    def test_passes_custom_requirements_through_to_the_prompt(self, mock_generate_json):
        mock_generate_json.return_value = {"lines": []}

        script_generator.generate_script(
            _scene_plan(), "Topic", custom_requirements="Always mention the year."
        )

        prompt_arg = mock_generate_json.call_args[0][0]
        self.assertIn("Always mention the year.", prompt_arg)

    @patch("app.departments.creative.script_generator.generate_json")
    def test_passes_format_through_to_the_prompt(self, mock_generate_json):
        mock_generate_json.return_value = {"lines": []}

        script_generator.generate_script(_scene_plan(), "Topic", format=Format.educational)

        prompt_arg = mock_generate_json.call_args[0][0]
        self.assertIn(script_generator.FORMAT_GUIDANCE[Format.educational], prompt_arg)

    @patch("app.departments.creative.script_generator.generate_json")
    def test_passes_corporate_format_through_to_the_prompt(self, mock_generate_json):
        mock_generate_json.return_value = {"lines": []}

        script_generator.generate_script(_scene_plan(), "Topic", format=Format.corporate)

        prompt_arg = mock_generate_json.call_args[0][0]
        self.assertIn(script_generator.FORMAT_GUIDANCE[Format.corporate], prompt_arg)

    def test_empty_scene_plan_short_circuits_without_llm_call(self):
        with patch("app.departments.creative.script_generator.generate_json") as mock_generate_json:
            script = script_generator.generate_script(ScenePlan(scenes=[]), "Topic")
            mock_generate_json.assert_not_called()
        self.assertEqual(script.full_text, "")
        self.assertEqual(script.lines, [])


if __name__ == "__main__":
    unittest.main()
