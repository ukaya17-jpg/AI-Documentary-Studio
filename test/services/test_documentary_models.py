import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import (
    PACING_SCENE_SPEC,
    Pacing,
    TopicCategory,
    resolve_pacing,
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


class TestTemplates(unittest.TestCase):
    def test_all_categories_have_a_template(self):
        for category in TopicCategory:
            template = get_template(category)
            self.assertIn("style", template)
            self.assertIn("opening_hook", template)
            self.assertIn("section_guidance", template)
            self.assertIn("closing", template)

    def test_get_template_falls_back_for_unknown(self):
        self.assertIs(get_template(TopicCategory.history), PROFILE_PROMPTS[TopicCategory.history])


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
