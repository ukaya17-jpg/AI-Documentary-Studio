import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import Pacing, TopicCategory
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


class TestRunPipelineWithMockedStages(unittest.TestCase):
    """
    Full pipeline wiring test with every LLM call and legacy media I/O call
    (TTS, stock-footage download, ffmpeg render) mocked at the service-function
    boundary. Each stage's own internals are already covered by its unit
    tests; this test only verifies that data flows correctly from one stage
    into the next and that the final DocumentaryProject is fully populated.
    """

    def setUp(self):
        research_plan = ResearchPlan(topic="The Fall of Rome")
        outline = Outline(
            title="The Fall of Rome",
            sections=[
                OutlineSection(title="Origins", summary="How Rome began", importance=5),
                OutlineSection(title="Decline", summary="The slow fall", importance=4),
            ],
        )
        scene_plan = ScenePlan(
            pacing=Pacing.short,
            scenes=[
                Scene(index=0, title="Origins", narration_beat="How Rome began", duration_seconds=5.0),
                Scene(index=1, title="Decline", narration_beat="The slow fall", duration_seconds=5.0),
            ],
        )
        script = Script(
            full_text="Rome began humbly.\n\nThen it all fell apart.",
            lines=[
                ScriptLine(scene_index=0, text="Rome began humbly."),
                ScriptLine(scene_index=1, text="Then it all fell apart."),
            ],
        )
        storyboard = Storyboard(
            shots=[
                StoryboardShot(scene_index=0, description="ruins", search_terms=["ancient ruins"]),
                StoryboardShot(scene_index=1, description="battle", search_terms=["battle field"]),
            ]
        )
        asset_plan = AssetPlan(
            candidates=[
                AssetCandidate(scene_index=0, search_term="ancient ruins"),
                AssetCandidate(scene_index=1, search_term="battle field"),
            ]
        )
        downloaded_asset_plan = asset_plan.model_copy(
            update={"downloaded_paths": ["/tmp/ruins.mp4", "/tmp/battle.mp4"]}
        )
        narration = AudioTrack(voice_file="/tmp/audio.mp3", subtitle_file="/tmp/subtitle.srt", duration_seconds=10.0)
        audio_plan = AudioPlan(narration=narration)
        timeline = Timeline(combined_video_path="/tmp/combined.mp4", total_duration=10.0)
        seo = SeoMetadata(title="The Fall of Rome", description="...", hashtags=["#history"])
        quality_verdict = QualityVerdict(
            coherence_score=4,
            pacing_fit_score=4,
            seo_quality_score=4,
            overall_score=4.0,
            passed=True,
            issues=[],
        )

        self.mocks = {
            "intent": patch(
                "app.pipeline.default_pipeline.intent_analyzer.analyze_intent",
                return_value={"language": "en", "topic_category": TopicCategory.history},
            ),
            "research": patch(
                "app.pipeline.default_pipeline.research_planner.generate_research_plan",
                return_value=research_plan,
            ),
            "outline": patch(
                "app.pipeline.default_pipeline.outline_generator.generate_outline", return_value=outline
            ),
            "scene": patch(
                "app.pipeline.default_pipeline.scene_planner.plan_scenes", return_value=scene_plan
            ),
            "script": patch(
                "app.pipeline.default_pipeline.script_generator.generate_script", return_value=script
            ),
            "storyboard": patch(
                "app.pipeline.default_pipeline.storyboard_generator.generate_storyboard",
                return_value=storyboard,
            ),
            "asset_gen": patch(
                "app.pipeline.default_pipeline.asset_generator.build_asset_plan", return_value=asset_plan
            ),
            "asset_dl": patch(
                "app.pipeline.default_pipeline.asset_downloader.download_assets",
                return_value=downloaded_asset_plan,
            ),
            "audio": patch(
                "app.pipeline.default_pipeline.audio_renderer.render_audio_plan", return_value=audio_plan
            ),
            "timeline": patch(
                "app.pipeline.default_pipeline.timeline_builder.build_timeline", return_value=timeline
            ),
            "seo": patch(
                "app.pipeline.default_pipeline.seo_generator.generate_seo_metadata", return_value=seo
            ),
            "video": patch(
                "app.pipeline.default_pipeline.video_renderer.render_final_video",
                return_value="/tmp/tasks/proj-1/final.mp4",
            ),
            "quality": patch(
                "app.pipeline.default_pipeline.quality_critic.evaluate_project",
                return_value=quality_verdict,
            ),
            "thumbnail": patch(
                "app.pipeline.default_pipeline.thumbnail_generator.generate_thumbnail",
                return_value="/tmp/tasks/proj-1/thumbnail.png",
            ),
        }
        self.started = {name: m.start() for name, m in self.mocks.items()}
        for m in self.mocks.values():
            self.addCleanup(m.stop)

        self.research_plan = research_plan
        self.outline = outline
        self.scene_plan = scene_plan
        self.script = script
        self.storyboard = storyboard
        self.asset_plan = asset_plan
        self.downloaded_asset_plan = downloaded_asset_plan
        self.narration = narration
        self.audio_plan = audio_plan
        self.timeline = timeline
        self.seo = seo
        self.quality_verdict = quality_verdict

    def test_full_pipeline_wiring(self):
        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
        )

        self.assertEqual(project.language, "en")
        self.assertEqual(project.topic_category, TopicCategory.history)
        self.assertIs(project.research_plan, self.research_plan)
        self.assertIs(project.outline, self.outline)
        self.assertIs(project.scene_plan, self.scene_plan)
        self.assertIs(project.script, self.script)
        self.assertIs(project.storyboard, self.storyboard)
        self.assertIs(project.asset_plan, self.downloaded_asset_plan)
        self.assertIs(project.audio_plan, self.audio_plan)
        self.assertIs(project.timeline, self.timeline)
        self.assertIs(project.seo, self.seo)
        self.assertEqual(project.final_video_path, "/tmp/tasks/proj-1/final.mp4")

        # outline_generator receives the research plan produced by research_planner.
        _, outline_kwargs = self.started["outline"].call_args
        self.assertIs(outline_kwargs["research_plan"], self.research_plan)
        self.assertEqual(outline_kwargs["topic_category"], TopicCategory.history)

        # scene_planner receives the outline and the resolved pacing.
        scene_args, scene_kwargs = self.started["scene"].call_args
        self.assertIs(scene_args[0], self.outline)
        self.assertEqual(scene_kwargs["pacing"], Pacing.short)

        # script_generator receives the scene plan and the outline (for
        # Hook/Retention/Callback story-craft instructions).
        script_args, script_kwargs = self.started["script"].call_args
        self.assertIs(script_args[0], self.scene_plan)
        self.assertIs(script_kwargs["outline"], self.outline)

        # storyboard_generator receives both scene plan and script.
        storyboard_args, _ = self.started["storyboard"].call_args
        self.assertIs(storyboard_args[0], self.scene_plan)
        self.assertIs(storyboard_args[1], self.script)

        # asset_generator receives the storyboard.
        asset_gen_args, _ = self.started["asset_gen"].call_args
        self.assertIs(asset_gen_args[0], self.storyboard)

        # asset_downloader receives the asset plan and the scene budget as the
        # audio-duration estimate (TTS hasn't run yet at that point).
        _, asset_dl_kwargs = self.started["asset_dl"].call_args
        self.assertIs(asset_dl_kwargs.get("asset_plan") or self.started["asset_dl"].call_args[0][0], self.asset_plan)
        self.assertEqual(asset_dl_kwargs["audio_duration"], self.scene_plan.total_duration)
        self.assertEqual(asset_dl_kwargs["task_id"], "proj-1")

        # timeline_builder receives the downloaded asset plan and the narration track.
        timeline_args, _ = self.started["timeline"].call_args
        self.assertIs(timeline_args[0], self.downloaded_asset_plan)
        self.assertIs(timeline_args[1], self.narration)

        # seo_generator receives the topic and script.
        seo_args, _ = self.started["seo"].call_args
        self.assertEqual(seo_args[0], "The Fall of Rome")
        self.assertIs(seo_args[1], self.script)

        # video_renderer receives the timeline and the narration track.
        video_args, video_kwargs = self.started["video"].call_args
        self.assertIs(video_args[0], self.timeline)
        self.assertIs(video_args[1], self.narration)
        self.assertEqual(video_kwargs["task_id"], "proj-1")
        self.assertEqual(video_kwargs["params"].video_subject, "The Fall of Rome")

        # quality_critic runs after the video is rendered (informational only)
        # and receives the fully-populated project.
        self.assertIs(project.quality_verdict, self.quality_verdict)
        quality_args, _ = self.started["quality"].call_args
        evaluated_project = quality_args[0]
        self.assertEqual(evaluated_project.final_video_path, "/tmp/tasks/proj-1/final.mp4")
        self.assertIs(evaluated_project.seo, self.seo)

        # thumbnail_generator receives the combined (pre-subtitle-burn) video
        # and the SEO metadata, not the final rendered video.
        self.assertEqual(project.thumbnail_path, "/tmp/tasks/proj-1/thumbnail.png")
        thumb_args, _ = self.started["thumbnail"].call_args
        self.assertEqual(thumb_args[0], self.timeline.combined_video_path)
        self.assertIs(thumb_args[1], self.seo)
        self.assertEqual(thumb_args[2], "proj-1")

    def test_final_video_path_is_set_even_when_quality_review_is_unavailable(self):
        self.started["quality"].return_value = None

        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
        )

        self.assertIsNone(project.quality_verdict)
        self.assertEqual(project.final_video_path, "/tmp/tasks/proj-1/final.mp4")

    def test_final_video_path_is_set_even_when_thumbnail_is_unavailable(self):
        self.started["thumbnail"].return_value = ""

        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
        )

        self.assertEqual(project.thumbnail_path, "")
        self.assertEqual(project.final_video_path, "/tmp/tasks/proj-1/final.mp4")


if __name__ == "__main__":
    unittest.main()
