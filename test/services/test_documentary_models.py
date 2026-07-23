import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import (
    DEFAULT_TONE_BY_CATEGORY,
    PACING_SCENE_SPEC,
    Format,
    Pacing,
    Tone,
    TopicCategory,
    resolve_format,
    resolve_pacing,
    resolve_tone,
    resolve_topic_category,
)
from app.config.templates import PROFILE_PROMPTS, get_template
from app.models.asset import AssetCandidate, AssetPlan
from app.models.audio import AudioPlan, AudioTrack
from app.models.documentary_project import DocumentaryProject
from app.models.outline import Outline, OutlineSection
from app.models.research_plan import ResearchPlan, ResearchQuestion
from app.models.scene import Scene, ScenePlan
from app.models.script import Script, ScriptLine
from app.models.seo import SeoMetadata
from app.models.storyboard import Storyboard, StoryboardShot
from app.models.timeline import Timeline, TimelineClip


class TestProfileDimensions(unittest.TestCase):
    def test_resolve_topic_category_valid_and_invalid(self):
        self.assertEqual(resolve_topic_category("history"), TopicCategory.history)
        self.assertEqual(resolve_topic_category("SPACE"), TopicCategory.space)
        self.assertIsNone(resolve_topic_category("not-a-category"))
        self.assertIsNone(resolve_topic_category(None))

    def test_resolve_pacing_defaults_on_invalid(self):
        self.assertEqual(resolve_pacing("long"), Pacing.long)
        self.assertEqual(resolve_pacing("bogus"), Pacing.short)
        self.assertEqual(resolve_pacing(None), Pacing.short)

    def test_pacing_scene_spec_has_both_pacings(self):
        self.assertIn(Pacing.short, PACING_SCENE_SPEC)
        self.assertIn(Pacing.long, PACING_SCENE_SPEC)
        self.assertEqual(PACING_SCENE_SPEC[Pacing.short]["scene_count"], 4)
        self.assertEqual(PACING_SCENE_SPEC[Pacing.long]["scene_count"], 7)

    def test_default_tone_by_category_matches_original_hard_locked_mapping(self):
        # This mapping IS the regression contract: resolve_tone() with no
        # override must reproduce exactly what each category used to get
        # hard-locked to before Tone existed as an independent dimension.
        self.assertEqual(DEFAULT_TONE_BY_CATEGORY[TopicCategory.travel], Tone.cinematic)
        self.assertEqual(DEFAULT_TONE_BY_CATEGORY[TopicCategory.history], Tone.credibility)
        self.assertEqual(DEFAULT_TONE_BY_CATEGORY[TopicCategory.space], Tone.epic)
        self.assertEqual(DEFAULT_TONE_BY_CATEGORY[TopicCategory.psychology], Tone.scientific)

    def test_resolve_tone_defaults_to_category_tone_when_no_override(self):
        for category, expected_tone in DEFAULT_TONE_BY_CATEGORY.items():
            self.assertEqual(resolve_tone(category, None), expected_tone)
            self.assertEqual(resolve_tone(category, ""), expected_tone)

    def test_resolve_tone_override_wins_regardless_of_category(self):
        self.assertEqual(resolve_tone(TopicCategory.travel, Tone.scientific), Tone.scientific)
        self.assertEqual(resolve_tone(TopicCategory.psychology, "epic"), Tone.epic)

    def test_resolve_tone_invalid_override_falls_back_to_category_default(self):
        self.assertEqual(resolve_tone(TopicCategory.space, "not-a-tone"), Tone.epic)

    def test_resolve_tone_unknown_category_falls_back_to_neutral(self):
        self.assertEqual(resolve_tone(None, None), Tone.neutral)
        self.assertEqual(resolve_tone("not-a-category", None), Tone.neutral)

    def test_resolve_format_valid_and_invalid(self):
        # Unlike resolve_tone, there's no category-based default to fall
        # back to -- None means "no format applied", not "unresolved".
        self.assertEqual(resolve_format("educational"), Format.educational)
        self.assertEqual(resolve_format("EDUCATIONAL"), Format.educational)
        self.assertEqual(resolve_format(Format.educational), Format.educational)
        self.assertIsNone(resolve_format(None))
        self.assertIsNone(resolve_format(""))
        self.assertIsNone(resolve_format("podcast"))  # not implemented yet
        self.assertIsNone(resolve_format("not-a-format"))


class TestTemplates(unittest.TestCase):
    def test_all_tones_have_a_template(self):
        for tone in Tone:
            template = get_template(tone)
            self.assertIn("style", template)
            self.assertIn("opening_hook", template)
            self.assertIn("section_guidance", template)
            self.assertIn("closing", template)

    def test_get_template_falls_back_for_unknown(self):
        self.assertIs(get_template(Tone.credibility), PROFILE_PROMPTS[Tone.credibility])
        self.assertIs(get_template(None), PROFILE_PROMPTS[Tone.credibility])
        # Tone.neutral has no dedicated template (no new prompt content
        # authored this phase) -- it deliberately reuses credibility's, the
        # same fallback get_template always had before Tone existed.
        self.assertIs(get_template(Tone.neutral), PROFILE_PROMPTS[Tone.credibility])


class TestModels(unittest.TestCase):
    def test_scene_plan_total_duration(self):
        plan = ScenePlan(
            pacing=Pacing.short,
            scenes=[
                Scene(index=0, title="a", duration_seconds=5.0),
                Scene(index=1, title="b", duration_seconds=5.0),
            ],
        )
        self.assertEqual(plan.total_duration, 10.0)

    def test_documentary_project_minimal_construction(self):
        project = DocumentaryProject(project_id="p1", topic="Roman Empire")
        self.assertEqual(project.pacing, Pacing.short)
        self.assertIsNone(project.topic_category)
        self.assertIsNone(project.tone)
        self.assertIsNone(project.format)
        self.assertIsNone(project.outline)

    def test_documentary_project_full_construction(self):
        project = DocumentaryProject(
            project_id="p1",
            topic="Roman Empire",
            topic_category=TopicCategory.history,
            pacing=Pacing.long,
            research_plan=ResearchPlan(
                topic="Roman Empire",
                key_questions=[ResearchQuestion(question="Why did it fall?")],
            ),
            outline=Outline(
                title="The Fall of Rome",
                sections=[OutlineSection(title="Origins", importance=5)],
            ),
            scene_plan=ScenePlan(scenes=[Scene(index=0, title="Origins")]),
            script=Script(full_text="Rome was not built in a day.", lines=[ScriptLine(scene_index=0, text="Rome was not built in a day.")]),
            storyboard=Storyboard(shots=[StoryboardShot(scene_index=0, description="wide shot of the forum")]),
            asset_plan=AssetPlan(candidates=[AssetCandidate(scene_index=0, search_term="ancient rome")]),
            audio_plan=AudioPlan(narration=AudioTrack(voice_name="tr-TR-AhmetNeural")),
            timeline=Timeline(clips=[TimelineClip(scene_index=0, video_path="/tmp/a.mp4")]),
            seo=SeoMetadata(title="The Fall of Rome"),
        )
        self.assertEqual(project.outline.sections[0].importance, 5)
        self.assertEqual(project.script.lines[0].scene_index, 0)


if __name__ == "__main__":
    unittest.main()
