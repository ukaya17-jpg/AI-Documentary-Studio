"""Systematic smoke-test matrix: every TopicCategory x Pacing x Tone x Format
combination must run_pipeline() without raising.

Unlike test_default_pipeline.py's TestRunPipelineWithMockedStages (which
checks detailed data wiring for one representative call), this file's only
job is breadth -- catching a combination that crashes (e.g. a KeyError in a
category/tone/format-keyed dict that only happens to be missing an entry)
faster than waiting for it to show up in a real run. Every LLM/media call is
mocked, so the whole matrix runs in a fraction of a second.
"""

import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import Format, Pacing, Tone, TopicCategory
from app.models.asset import AssetCandidate, AssetPlan
from app.models.audio import AudioPlan, AudioTrack
from app.models.outline import Outline, OutlineSection
from app.models.quality import QualityVerdict
from app.models.research_plan import ResearchPlan
from app.models.scene import Scene, ScenePlan
from app.models.script import Script, ScriptLine
from app.models.seo import SeoMetadata
from app.models.storyboard import Storyboard, StoryboardShot
from app.models.timeline import Timeline
from app.pipeline import default_pipeline
from app.utils import utils

_TOPIC_CATEGORY_CHOICES = [None] + list(TopicCategory)
_TONE_CHOICES = [None] + list(Tone)
_FORMAT_CHOICES = [None] + list(Format)


class TestPipelineDimensionMatrix(unittest.TestCase):
    def setUp(self):
        research_plan = ResearchPlan(topic="Matrix Topic", key_facts=["A fact."])
        outline = Outline(
            title="Matrix Topic",
            sections=[OutlineSection(title="Section", summary="Summary", importance=3)],
        )
        scene_plan = ScenePlan(
            pacing=Pacing.short,
            scenes=[Scene(index=0, title="Scene", narration_beat="Beat", duration_seconds=5.0)],
        )
        script = Script(
            full_text="Narration line.",
            lines=[ScriptLine(scene_index=0, text="Narration line.")],
        )
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="shot", search_terms=["term"])]
        )
        asset_plan = AssetPlan(candidates=[AssetCandidate(scene_index=0, search_term="term")])
        downloaded_asset_plan = asset_plan.model_copy(update={"downloaded_paths": ["/tmp/clip.mp4"]})
        narration = AudioTrack(
            voice_file="/tmp/audio.mp3", subtitle_file="/tmp/subtitle.srt", duration_seconds=5.0
        )
        audio_plan = AudioPlan(narration=narration)
        timeline = Timeline(combined_video_path="/tmp/combined.mp4", total_duration=5.0)
        seo = SeoMetadata(title="Matrix Topic", description="...", hashtags=["#tag"])
        quality_verdict = QualityVerdict(
            coherence_score=4, pacing_fit_score=4, seo_quality_score=4,
            overall_score=4.0, passed=True, issues=[],
        )

        def fake_analyze_intent(topic, language="auto", topic_category_override=None):
            category = topic_category_override or TopicCategory.history
            if isinstance(category, str):
                category = TopicCategory(category)
            return {"language": "en", "topic_category": category}

        self.mocks = {
            "intent": patch(
                "app.pipeline.default_pipeline.intent_analyzer.analyze_intent",
                side_effect=fake_analyze_intent,
            ),
            "research": patch(
                "app.pipeline.default_pipeline.research_planner.generate_research_plan",
                return_value=research_plan,
            ),
            "outline": patch(
                "app.pipeline.default_pipeline.outline_generator.generate_outline",
                return_value=outline,
            ),
            "scene": patch(
                "app.pipeline.default_pipeline.scene_planner.plan_scenes", return_value=scene_plan
            ),
            "script": patch(
                "app.pipeline.default_pipeline.script_generator.generate_script",
                return_value=script,
            ),
            "storyboard": patch(
                "app.pipeline.default_pipeline.storyboard_generator.generate_storyboard",
                return_value=storyboard,
            ),
            "asset_gen": patch(
                "app.pipeline.default_pipeline.asset_generator.build_asset_plan",
                return_value=asset_plan,
            ),
            "asset_dl": patch(
                "app.pipeline.default_pipeline.asset_downloader.download_assets",
                return_value=downloaded_asset_plan,
            ),
            "audio": patch(
                "app.pipeline.default_pipeline.audio_renderer.render_audio_plan",
                return_value=audio_plan,
            ),
            "timeline": patch(
                "app.pipeline.default_pipeline.timeline_builder.build_timeline",
                return_value=timeline,
            ),
            "seo": patch(
                "app.pipeline.default_pipeline.seo_generator.generate_seo_metadata",
                return_value=seo,
            ),
            "video": patch(
                "app.pipeline.default_pipeline.video_renderer.render_final_video",
                return_value="/tmp/tasks/matrix/final.mp4",
            ),
            "quality": patch(
                "app.pipeline.default_pipeline.quality_critic.evaluate_project",
                return_value=quality_verdict,
            ),
            "thumbnail": patch(
                "app.pipeline.default_pipeline.thumbnail_generator.generate_thumbnail",
                return_value="/tmp/tasks/matrix/thumbnail.png",
            ),
        }
        for m in self.mocks.values():
            m.start()
            self.addCleanup(m.stop)

    def test_all_category_pacing_tone_format_combinations_run_without_raising(self):
        for category in _TOPIC_CATEGORY_CHOICES:
            for pacing in Pacing:
                for tone in _TONE_CHOICES:
                    for fmt in _FORMAT_CHOICES:
                        project_id = (
                            f"matrix-{category}-{pacing}-{tone}-{fmt}".replace(" ", "_")
                        )
                        # Registered before the call so a real (non-assertion)
                        # exception mid-matrix still cleans up every task_dir
                        # created so far, not just ones reached after this loop.
                        self.addCleanup(
                            lambda pid=project_id: shutil.rmtree(
                                utils.task_dir(pid), ignore_errors=True
                            )
                        )
                        with self.subTest(
                            category=category, pacing=pacing, tone=tone, format=fmt
                        ):
                            project = default_pipeline.run_pipeline(
                                project_id=project_id,
                                topic="Matrix Topic",
                                language="auto",
                                topic_category_override=category,
                                tone=tone,
                                format=fmt,
                                pacing=pacing,
                                voice_name="en-US-JennyNeural",
                            )
                            self.assertEqual(
                                project.final_video_path, "/tmp/tasks/matrix/final.mp4"
                            )
                            self.assertIsNotNone(project.tone)
                            if fmt is None:
                                self.assertIsNone(project.format)
                            else:
                                self.assertEqual(project.format, fmt)


if __name__ == "__main__":
    unittest.main()
