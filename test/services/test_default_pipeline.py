import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import Format, Pacing, Tone, TopicCategory
from app.config import characters
from app.models.asset import AssetCandidate, AssetPlan
from app.models.audio import AudioPlan, AudioTrack
from app.models.documentary_project import DocumentaryProject
from app.models.outline import Outline, OutlineSection
from app.models.quality import QualityVerdict
from app.models.research_plan import ResearchPlan
from app.models.schema import VideoConcatMode
from app.models.scene import Scene, ScenePlan
from app.models.script import Script, ScriptLine
from app.models.seo import SeoMetadata
from app.models.storyboard import Storyboard, StoryboardShot
from app.models.timeline import Timeline
from app.pipeline import default_pipeline
from app.utils import utils


class TestRunPipelineWithMockedStages(unittest.TestCase):
    """
    Full pipeline wiring test with every LLM call and legacy media I/O call
    (TTS, stock-footage download, ffmpeg render) mocked at the service-function
    boundary. Each stage's own internals are already covered by its unit
    tests; this test only verifies that data flows correctly from one stage
    into the next and that the final DocumentaryProject is fully populated.
    """

    def setUp(self):
        research_plan = ResearchPlan(
            topic="The Fall of Rome",
            key_facts=[
                "Rome was founded in 753 BC.",
                "The Senate governed the Republic.",
                "The empire split into east and west in 395 CE.",
                "This fourth fact should be dropped by the [:3] slice.",
            ],
        )
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
            "thumbnail_b": patch(
                "app.pipeline.default_pipeline.thumbnail_generator.generate_thumbnail_variant_b",
                return_value="/tmp/tasks/proj-1/thumbnail_b.png",
            ),
            "thumbnail_c": patch(
                "app.pipeline.default_pipeline.thumbnail_generator.generate_thumbnail_variant_c",
                return_value="/tmp/tasks/proj-1/thumbnail_c.png",
            ),
            "thumbnail_d": patch(
                "app.pipeline.default_pipeline.thumbnail_generator.generate_thumbnail_variant_d",
                return_value="/tmp/tasks/proj-1/thumbnail_d.png",
            ),
        }
        self.started = {name: m.start() for name, m in self.mocks.items()}
        for m in self.mocks.values():
            self.addCleanup(m.stop)

        # _save_project_snapshot() writes a real file under storage/tasks/
        # (not mocked -- it's the thing under test in some cases below).
        self.addCleanup(lambda: shutil.rmtree(utils.task_dir("proj-1"), ignore_errors=True))

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
            custom_system_prompt="Write like a noir detective.",
            custom_requirements="Always mention exact dates.",
            stock_keyword_hint="Ottoman archives",
        )

        self.assertEqual(project.language, "en")
        self.assertEqual(project.topic_category, TopicCategory.history)
        # No tone override passed -- resolves to history's default tone,
        # reproducing the category's old hard-locked behavior.
        self.assertEqual(project.tone, Tone.credibility)
        # No format passed -- must stay None, exactly as before Format existed.
        self.assertIsNone(project.format)
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

        # research_planner receives the resolved tone (history's default:
        # credibility) AND the resolved topic_category (GÖREV 1 -- needed so
        # generate_research_plan can discard a web-search grounding result
        # whose text signals a different category, e.g. topic "Roma"
        # resolving to AS Roma the football club instead of the city).
        _, research_kwargs = self.started["research"].call_args
        self.assertEqual(research_kwargs["tone"], Tone.credibility)
        self.assertEqual(research_kwargs["topic_category"], TopicCategory.history)

        # outline_generator receives the research plan produced by research_planner,
        # the same resolved tone, and the resolved pacing (GÖREV 2 -- needed
        # so extended pacing's outline actually requests enough sections for
        # its 20-scene budget instead of the short/long default "4-7").
        _, outline_kwargs = self.started["outline"].call_args
        self.assertIs(outline_kwargs["research_plan"], self.research_plan)
        self.assertEqual(outline_kwargs["tone"], Tone.credibility)
        self.assertEqual(outline_kwargs["pacing"], Pacing.short)

        # scene_planner receives the outline and the resolved pacing.
        scene_args, scene_kwargs = self.started["scene"].call_args
        self.assertIs(scene_args[0], self.outline)
        self.assertEqual(scene_kwargs["pacing"], Pacing.short)

        # script_generator receives the scene plan, the outline (for
        # Hook/Retention/Callback story-craft instructions), and the resolved
        # tone (previously script_generator never saw tone/category at all).
        script_args, script_kwargs = self.started["script"].call_args
        self.assertIs(script_args[0], self.scene_plan)
        self.assertIs(script_kwargs["outline"], self.outline)
        self.assertEqual(script_kwargs["tone"], Tone.credibility)
        self.assertIsNone(script_kwargs["format"])
        # GÖREV F (kullanıcı onaylı): custom_system_prompt zaten
        # script_generator'a kadar kablolanmıştı ama run_pipeline() hiç
        # almıyordu -- custom_requirements ise tamamen yeni bir parametre.
        # İkisi de doğrudan generate_script()'e ulaşmalı, ayrıca projede de
        # (şeffaflık/kayıt için) saklanmalı.
        self.assertEqual(
            script_kwargs["custom_system_prompt"], "Write like a noir detective."
        )
        self.assertEqual(
            script_kwargs["custom_requirements"], "Always mention exact dates."
        )
        self.assertEqual(project.custom_system_prompt, "Write like a noir detective.")
        self.assertEqual(project.custom_requirements, "Always mention exact dates.")

        # storyboard_generator receives both scene plan and script, plus the
        # topic and a bounded slice of research key_facts -- these anchor the
        # LLM's search terms in the actual topic instead of falling back to
        # the generic nouns in the category guidance (e.g. "old map").
        storyboard_args, storyboard_kwargs = self.started["storyboard"].call_args
        self.assertIs(storyboard_args[0], self.scene_plan)
        self.assertIs(storyboard_args[1], self.script)
        self.assertEqual(storyboard_kwargs["topic"], "The Fall of Rome")
        self.assertEqual(
            storyboard_kwargs["key_facts"],
            [
                "Rome was founded in 753 BC.",
                "The Senate governed the Republic.",
                "The empire split into east and west in 395 CE.",
            ],
        )
        # "Stok Arama Kelimesi İpucu" (kullanıcı onaylı): brand-new parameter,
        # must reach storyboard_generator and also be recorded on the project
        # for transparency (same pattern as custom_system_prompt/custom_requirements
        # above).
        self.assertEqual(storyboard_kwargs["stock_keyword_hint"], "Ottoman archives")
        self.assertEqual(project.stock_keyword_hint, "Ottoman archives")

        # asset_generator receives the storyboard, the resolved topic
        # category (needed for the film_highlights AI-video likeness guard --
        # harmless for every other category/provider), and the real script
        # (needed for per-scene AI clip duration selection -- harmless for
        # the stock path, which ignores it).
        asset_gen_args, asset_gen_kwargs = self.started["asset_gen"].call_args
        self.assertIs(asset_gen_args[0], self.storyboard)
        self.assertEqual(asset_gen_kwargs["topic_category"], TopicCategory.history)
        self.assertIs(asset_gen_kwargs["script"], self.script)

        # asset_downloader receives the asset plan and a safety-padded scene
        # budget as the audio-duration estimate (TTS hasn't run yet at that
        # point, and real narration audio commonly runs well past the raw
        # scene-duration total -- see _ASSET_DOWNLOAD_DURATION_SAFETY_MULTIPLIER).
        _, asset_dl_kwargs = self.started["asset_dl"].call_args
        self.assertIs(asset_dl_kwargs.get("asset_plan") or self.started["asset_dl"].call_args[0][0], self.asset_plan)
        self.assertEqual(
            asset_dl_kwargs["audio_duration"],
            self.scene_plan.total_duration
            * default_pipeline._ASSET_DOWNLOAD_DURATION_SAFETY_MULTIPLIER,
        )
        self.assertEqual(asset_dl_kwargs["task_id"], "proj-1")

        # timeline_builder receives the downloaded asset plan and the narration track.
        timeline_args, _ = self.started["timeline"].call_args
        self.assertIs(timeline_args[0], self.downloaded_asset_plan)
        self.assertIs(timeline_args[1], self.narration)

        # seo_generator receives the topic, script, scene plan (for chapters),
        # and the same bounded slice of research key_facts as storyboard --
        # without this, the SEO caption/description has no grounding for
        # facts the script itself may state only vaguely (e.g. a site's
        # exact settlement timescale), and can invent a wrong one (real prod
        # bug: caption said "centuries" when key_facts said "~3,000 years").
        seo_args, seo_kwargs = self.started["seo"].call_args
        self.assertEqual(seo_args[0], "The Fall of Rome")
        self.assertIs(seo_args[1], self.script)
        self.assertIs(seo_kwargs["scene_plan"], self.scene_plan)
        self.assertEqual(
            seo_kwargs["key_facts"],
            [
                "Rome was founded in 753 BC.",
                "The Senate governed the Republic.",
                "The empire split into east and west in 395 CE.",
            ],
        )

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

        # Additional thumbnail choices (B/C/D compare) are generated the same
        # way, only attempted because variant A succeeded above.
        self.assertEqual(project.thumbnail_variant_b_path, "/tmp/tasks/proj-1/thumbnail_b.png")
        thumb_b_args, _ = self.started["thumbnail_b"].call_args
        self.assertEqual(thumb_b_args[0], self.timeline.combined_video_path)
        self.assertIs(thumb_b_args[1], self.seo)
        self.assertEqual(thumb_b_args[2], "proj-1")

        self.assertEqual(project.thumbnail_variant_c_path, "/tmp/tasks/proj-1/thumbnail_c.png")
        thumb_c_args, _ = self.started["thumbnail_c"].call_args
        self.assertEqual(thumb_c_args[0], self.timeline.combined_video_path)
        self.assertIs(thumb_c_args[1], self.seo)
        self.assertEqual(thumb_c_args[2], "proj-1")

        self.assertEqual(project.thumbnail_variant_d_path, "/tmp/tasks/proj-1/thumbnail_d.png")
        thumb_d_args, _ = self.started["thumbnail_d"].call_args
        self.assertEqual(thumb_d_args[0], self.timeline.combined_video_path)
        self.assertIs(thumb_d_args[1], self.seo)
        self.assertEqual(thumb_d_args[2], "proj-1")

    def test_character_references_reach_audio_asset_and_ai_video_stages(self):
        # "Karakter Sesi" planı (kullanıcı onaylı, Seçenek A): character_
        # references, asset/ai_video aşamalarının yanına, audio (TTS)
        # aşamasına da AYNEN geçirilmeli -- audio_renderer'ın kendisi tek-
        # karakter/çoklu-karakter ayrımını içeride çözüyor (bkz.
        # test_audio_renderer.py), burada sadece doğru şekilde İLETİLDİĞİ
        # doğrulanıyor.
        from app.models.character import CharacterReference

        bao = CharacterReference(name="Bao", frontal_image_url="data:image/jpeg;base64,x")

        default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            character_references=[bao],
        )

        _args, audio_kwargs = self.started["audio"].call_args
        self.assertEqual(audio_kwargs["character_references"], [bao])

    def test_location_references_reach_asset_and_ai_video_stages_but_not_audio(self):
        # "Mekan Sistemi" planı (kullanıcı onaylı): location_references,
        # character_references ile AYNI @ElementN mekanizmasını paylaşıyor
        # (asset/ai_video aşamalarında İKİSİ DE, sırayla, tek bir listede
        # birleşmiş olarak görünmeli) -- ama audio_renderer'a ASLA
        # ulaşmamalı (bkz. run_pipeline'ın location_references docstring'i:
        # audio_renderer'ın "Karakter Sesi" mekanizması
        # len(character_references) == 1 kontrolüne dayanıyor, bir mekan bu
        # sayıyı 2'ye çıkarıp karakterin ses eşlemesini SESSİZCE bozardı).
        from app.models.character import CharacterReference

        bao = CharacterReference(name="Bao", frontal_image_url="data:image/jpeg;base64,x")
        library = CharacterReference(name="Kütüphane", frontal_image_url="data:image/jpeg;base64,y")

        with patch(
            "app.pipeline.default_pipeline.ai_video_generator.generate_ai_clips",
            return_value=self.downloaded_asset_plan,
        ) as mock_generate_ai_clips:
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                video_source="ai_generated",
                character_references=[bao],
                location_references=[library],
            )

        # Stage 7 (asset_generator.build_asset_plan): karakter + mekan,
        # SIRAYLA, tek listede, HER sahne için (auto olmadığında sabit
        # seçim her scene_index'e aynen kopyalanır -- bkz.
        # _resolve_references_by_scene'in docstring'i).
        _, asset_gen_kwargs = self.started["asset_gen"].call_args
        self.assertEqual(
            asset_gen_kwargs["character_references_by_scene"],
            {0: [bao, library], 1: [bao, library]},
        )

        # Stage 8 (ai_video_generator.generate_ai_clips): AYNI birleşik sözlük.
        _, ai_video_kwargs = mock_generate_ai_clips.call_args
        self.assertEqual(
            ai_video_kwargs["character_references_by_scene"],
            {0: [bao, library], 1: [bao, library]},
        )

        # Stage 9 (audio_renderer): SADECE karakter -- mekan hiç ulaşmıyor.
        _, audio_kwargs = self.started["audio"].call_args
        self.assertEqual(audio_kwargs["character_references"], [bao])

    def test_location_only_selection_never_reaches_audio_stage(self):
        # Karaktersiz + sadece mekan seçili bir proje: audio_renderer'a
        # character_references=[] (boş) gitmeli -- [location] DEĞİL. Bu,
        # ses override mekanizmasının hiç tetiklenmemesini garanti eder.
        from app.models.character import CharacterReference

        library = CharacterReference(name="Kütüphane", frontal_image_url="data:image/jpeg;base64,y")

        default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            location_references=[library],
        )

        _, audio_kwargs = self.started["audio"].call_args
        self.assertFalse(audio_kwargs["character_references"])

        _, asset_gen_kwargs = self.started["asset_gen"].call_args
        self.assertEqual(
            asset_gen_kwargs["character_references_by_scene"], {0: [library], 1: [library]}
        )

    def test_auto_character_selection_triggers_per_scene_casting(self):
        # "Sahne Bazlı Otomatik Kadrolama" planı (kullanıcı onaylı): Auto
        # modda casting_generator çağrılıyor VE her sahne KENDİ karakterini
        # alabiliyor -- sahne 0 professor_nova, sahne 1 hiç karaktersiz.
        # character_references (düz liste) bu modda TAMAMEN görmezden
        # gelinmeli (auto_character=True iken göz ardı edilir).
        from app.models.character import CharacterReference

        should_be_ignored = CharacterReference(
            name="Should Be Ignored", frontal_image_url="data:image/jpeg;base64,z"
        )
        nova_ref = CharacterReference(
            name="Professor Nova", frontal_image_url="data:image/jpeg;base64,nova"
        )

        with patch(
            "app.pipeline.default_pipeline.casting_generator.generate_casting_plan",
            return_value={
                0: {"characters": ["professor_nova"], "location": None},
                1: {"characters": [], "location": None},
            },
        ) as mock_casting, patch(
            "app.pipeline.default_pipeline.characters.get_character_reference",
            return_value=nova_ref,
        ):
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                character_references=[should_be_ignored],
                character_selection=characters.AUTO_CHARACTER,
            )

        mock_casting.assert_called_once()
        _, asset_gen_kwargs = self.started["asset_gen"].call_args
        self.assertEqual(
            asset_gen_kwargs["character_references_by_scene"],
            {0: [nova_ref], 1: []},
        )
        # Auto modda tek bir "sabit karakter" yok -- ses override hiç
        # tetiklenmemeli (bkz. run_pipeline'ın character_selection
        # docstring paragrafı).
        _, audio_kwargs = self.started["audio"].call_args
        self.assertEqual(audio_kwargs["character_references"], [should_be_ignored])

    def test_auto_character_with_realistic_none_input_never_leaks_into_audio_override(self):
        # VS Code denetim raporu (madde 2, ⚠️): önceki test yapay bir
        # character_references=[should_be_ignored] değeri kullanıyordu --
        # bu, GERÇEK webui davranışını (Auto modda character_references
        # HER ZAMAN None/boş gelir, resolve_character_selection("auto")
        # kayıtlı bir slug olmadığı için [] döner) yansıtmıyordu. Bu test
        # gerçekçi girdiyle VE casting'in HER sahnede AYNI karakteri
        # (professor_nova) seçtiği -- yani "tek bir sabit karakter" gibi
        # GÖRÜNEN -- en zorlayıcı senaryoyla, ses override'ının yine de
        # HİÇ tetiklenmediğini kanıtlıyor.
        from app.models.character import CharacterReference

        nova_ref = CharacterReference(
            name="Professor Nova", frontal_image_url="data:image/jpeg;base64,nova"
        )

        with patch(
            "app.pipeline.default_pipeline.casting_generator.generate_casting_plan",
            return_value={
                0: {"characters": ["professor_nova"], "location": None},
                1: {"characters": ["professor_nova"], "location": None},
            },
        ), patch(
            "app.pipeline.default_pipeline.characters.get_character_reference",
            return_value=nova_ref,
        ):
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                character_references=None,
                character_selection=characters.AUTO_CHARACTER,
            )

        # Görsel tarafta (asset_gen) her iki sahne de professor_nova alıyor
        # -- casting gerçekten çalışıyor.
        _, asset_gen_kwargs = self.started["asset_gen"].call_args
        self.assertEqual(
            asset_gen_kwargs["character_references_by_scene"],
            {0: [nova_ref], 1: [nova_ref]},
        )
        # Ama ses tarafı: character_references=None geldiği için
        # audio_renderer'a da None/falsy gitmeli -- casting'in HER sahnede
        # aynı karakteri seçmiş olması, ses override'ını TETİKLEMEMELİ.
        # (_resolve_narration_voice sadece FIXED character_references
        # listesine bakıyor, casting_by_scene'e hiç erişimi yok.)
        _, audio_kwargs = self.started["audio"].call_args
        self.assertFalse(audio_kwargs["character_references"])

    def test_casting_by_scene_reaches_audio_stage(self):
        # "Sahne Bazlı Gerçek Ses Değişimi" planı (kullanıcı onaylı):
        # casting_generator'ın ham per-scene kararı (casting_by_scene),
        # references_by_scene'in yanında audio_renderer.render_audio_plan()'a
        # da ulaşmalı -- render_audio_plan kendi içinde hangi sahnenin
        # hangi karakterin sesini kullanacağına karar veriyor (bkz.
        # test_audio_renderer.py'nin TestRenderNarrationByScene'i).
        from app.models.character import CharacterReference

        nova_ref = CharacterReference(
            name="Professor Nova", frontal_image_url="data:image/jpeg;base64,nova"
        )
        raw_casting = {
            0: {"characters": ["professor_nova"], "location": None},
            1: {"characters": [], "location": None},
        }

        with patch(
            "app.pipeline.default_pipeline.casting_generator.generate_casting_plan",
            return_value=raw_casting,
        ), patch(
            "app.pipeline.default_pipeline.characters.get_character_reference",
            return_value=nova_ref,
        ):
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                character_selection=characters.AUTO_CHARACTER,
            )

        _, audio_kwargs = self.started["audio"].call_args
        self.assertEqual(audio_kwargs["casting_by_scene"], raw_casting)

    def test_non_auto_selection_passes_empty_casting_by_scene_to_audio(self):
        # Regresyon garantisi: Auto DEĞİLSE casting_by_scene audio'ya {}
        # (falsy) gitmeli -- render_audio_plan'ın bunu görünce eski
        # tek-çağrılı yolu (render_narration) kullanmaya devam etmesi
        # gerekir (bkz. test_audio_renderer.py'nin dispatch testleri).
        default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
        )

        _, audio_kwargs = self.started["audio"].call_args
        self.assertFalse(audio_kwargs["casting_by_scene"])

    def test_non_auto_character_selection_never_calls_casting_generator(self):
        # Regresyon garantisi: character_selection None/"none"/gerçek bir
        # slug iken casting_generator'a HİÇ dokunulmamalı -- LLM çağrısı
        # yok, ekstra maliyet yok.
        with patch(
            "app.pipeline.default_pipeline.casting_generator.generate_casting_plan"
        ) as mock_casting:
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
            )

        mock_casting.assert_not_called()

    def test_ai_generated_video_source_calls_ai_video_generator_not_asset_downloader(self):
        # Opt-in AI-generated video clips (fal.ai/Kling) branch at stage 8:
        # asset_downloader (the free/instant stock path) must not run at
        # all, and ai_video_generator gets the resolved aspect_ratio/duration
        # plus the on_substage_progress passthrough -- a single stage-level
        # message isn't enough feedback for a stage that can take many
        # minutes (real fal.ai generation time, not stock-download seconds).
        progress_calls = []
        with patch(
            "app.pipeline.default_pipeline.ai_video_generator.generate_ai_clips",
            return_value=self.downloaded_asset_plan,
        ) as mock_generate_ai_clips:
            project = default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.long,
                voice_name="en-US-JennyNeural",
                video_source="ai_generated",
                video_aspect="9:16",
                on_substage_progress=lambda done, total: progress_calls.append((done, total)),
            )

        self.assertIs(project.asset_plan, self.downloaded_asset_plan)
        self.started["asset_dl"].assert_not_called()
        mock_generate_ai_clips.assert_called_once()
        args, kwargs = mock_generate_ai_clips.call_args
        self.assertIs(args[0], self.asset_plan)
        self.assertEqual(kwargs["task_id"], "proj-1")
        self.assertEqual(kwargs["aspect_ratio"], "9:16")
        # generate_ai_clips() no longer takes a single global duration --
        # each candidate's own ai_duration (set per-scene by asset_generator
        # from real script word counts, see the "tekrar eden kare" fix) is
        # used instead. That per-scene selection is asset_generator's own
        # responsibility/tests; here we only confirm no stray "duration"
        # kwarg is passed anymore (would be a silent no-op/TypeError risk).
        self.assertNotIn("duration", kwargs)
        # Actually invoke the passed-through callback to prove it's the same
        # one given to run_pipeline(), not a lost/dropped reference.
        kwargs["on_substage_progress"](3, 7)
        self.assertEqual(progress_calls, [(3, 7)])

        # asset_generator now also receives the real script (stage 5 already
        # ran by stage 7) so it can compute per-scene AI clip durations from
        # real narration word counts instead of the pre-generation Pacing
        # target -- the root cause of the "repeated frame" bug this fixes.
        _, asset_gen_kwargs = self.started["asset_gen"].call_args
        self.assertIs(asset_gen_kwargs["script"], self.script)

    def test_ai_generated_video_uses_sequential_concat_mode(self):
        # "Sahne Bazlı Gerçek Ses Değişimi" ön koşulu (kullanıcı onaylı):
        # AI-üretilen video, her sahne için ayrı ayrı (asset_plan.candidates
        # sırasıyla) üretilmiş TEK bir klip -- random modda karıştırmak
        # sahne<->anlatım (ve artık sahne<->karakter sesi) eşleşmesini
        # bozar. SADECE bu kaynak için sequential'a geçiliyor -- stok
        # görüntünün kendi çeşitlilik amacı (aşağıdaki test) etkilenmiyor.
        with patch(
            "app.pipeline.default_pipeline.ai_video_generator.generate_ai_clips",
            return_value=self.downloaded_asset_plan,
        ):
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                video_source="ai_generated",
            )

        _, timeline_kwargs = self.started["timeline"].call_args
        self.assertEqual(timeline_kwargs["video_concat_mode"], VideoConcatMode.sequential)

    def test_stock_video_source_keeps_random_concat_mode(self):
        # Regresyon garantisi: varsayılan (pexels/vb.) kaynak hiç
        # değişmemeli -- random mod, aynı arama teriminden gelen birden
        # fazla klip arasında çeşitlilik için hâlâ doğru davranış.
        default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
        )

        _, timeline_kwargs = self.started["timeline"].call_args
        self.assertEqual(timeline_kwargs["video_concat_mode"], VideoConcatMode.random)

    def test_on_stage_change_called_for_all_12_stages_in_order(self):
        # Modernizasyon B: on_stage_change purely additive, must not change
        # anything about what run_pipeline() does -- only observed here.
        calls = []
        default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            on_stage_change=lambda n, name: calls.append((n, name)),
        )

        self.assertEqual(
            calls,
            [
                (1, "intent"),
                (2, "research"),
                (3, "outline"),
                (4, "scene"),
                (5, "script"),
                (6, "storyboard"),
                (7, "asset"),
                (8, "asset download"),
                (9, "audio (TTS)"),
                (10, "timeline"),
                (11, "seo"),
                (12, "video render"),
            ],
        )

    def test_omitting_on_stage_change_behaves_identically(self):
        # Regression: every pre-existing caller (CLI, every other test in
        # this file) never passes on_stage_change -- must be a true no-op.
        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
        )
        self.assertEqual(project.final_video_path, "/tmp/tasks/proj-1/final.mp4")

    def test_omitting_stock_keyword_hint_behaves_identically(self):
        # Regression: every pre-existing caller never passed stock_keyword_hint
        # -- it must default to "" and reach storyboard_generator as "", the
        # exact same value it always received before this parameter existed.
        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
        )
        self.assertEqual(project.final_video_path, "/tmp/tasks/proj-1/final.mp4")
        self.assertEqual(project.stock_keyword_hint, "")
        _, storyboard_kwargs = self.started["storyboard"].call_args
        self.assertEqual(storyboard_kwargs["stock_keyword_hint"], "")

    def test_tone_override_wins_over_category_default(self):
        # Category resolves to history -> credibility by default (see
        # test_full_pipeline_wiring), but an explicit override must win.
        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            tone=Tone.scientific,
        )

        self.assertEqual(project.tone, Tone.scientific)
        self.assertEqual(self.started["research"].call_args[1]["tone"], Tone.scientific)
        self.assertEqual(self.started["outline"].call_args[1]["tone"], Tone.scientific)
        self.assertEqual(self.started["script"].call_args[1]["tone"], Tone.scientific)

    def test_format_flows_only_to_script_not_research_or_outline(self):
        # Format has no category-based default (unlike tone) and only
        # script_generator was wired to receive it this phase -- research/
        # outline are untouched by design (see PROGRESS.md).
        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            format=Format.educational,
        )

        self.assertEqual(project.format, Format.educational)
        self.assertEqual(self.started["script"].call_args[1]["format"], Format.educational)
        self.assertNotIn("format", self.started["research"].call_args[1])
        self.assertNotIn("format", self.started["outline"].call_args[1])

    def test_kids_format_defaults_tone_to_nurturing_regardless_of_category(self):
        # "Ton Varsayılanı" planı (kullanıcı onaylı): "The Fall of Rome" ->
        # topic_category=history -> normalde Tone.credibility (bkz.
        # test_tone_override_wins_over_category_default) -- ama Format.kids
        # ile, tone_override YOKKEN, kategoriden BAĞIMSIZ Tone.nurturing
        # kullanılmalı.
        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            format=Format.kids,
        )

        self.assertEqual(project.tone, Tone.nurturing)
        self.assertEqual(self.started["script"].call_args[1]["tone"], Tone.nurturing)

    def test_kids_format_explicit_tone_override_still_wins(self):
        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            format=Format.kids,
            tone=Tone.epic,
        )

        self.assertEqual(project.tone, Tone.epic)

    def test_non_kids_format_tone_default_is_unaffected(self):
        # Regresyon garantisi: Kids DIŞINDAKİ formatlar topic_category'nin
        # kendi varsayılan tonunu (history -> credibility) hiç etkilemiyor.
        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            format=Format.educational,
        )

        self.assertEqual(project.tone, Tone.credibility)

    def test_video_style_flows_to_script_generator(self):
        default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            video_style="engagement_cta",
        )

        self.assertEqual(self.started["script"].call_args[1]["video_style"], "engagement_cta")

    def test_video_style_defaults_to_informational(self):
        # Regresyon garantisi: video_style hiç geçilmezse script_generator
        # eskisiyle birebir aynı ("informational", no-op) davranışı almalı.
        default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
        )

        self.assertEqual(self.started["script"].call_args[1]["video_style"], "informational")

    def test_auto_casting_assigns_multiple_characters_to_the_same_scene(self):
        # "Çoklu Karakter Aynı Sahnede" planı (kullanıcı onaylı): bir sahneye
        # 2+ karakter atanabiliyor -- character_references_by_scene, LİSTE
        # SIRASINI koruyarak ikisini de içermeli (asset_generator'ın
        # @Element1/@Element2 sırası bu listeye dayanıyor).
        from app.models.character import CharacterReference

        registry_refs = {
            "professor_nova": CharacterReference(
                name="Professor Nova", frontal_image_url="data:image/jpeg;base64,nova"
            ),
            "robo": CharacterReference(
                name="Robo", frontal_image_url="data:image/jpeg;base64,robo"
            ),
        }

        with patch(
            "app.pipeline.default_pipeline.casting_generator.generate_casting_plan",
            return_value={
                0: {"characters": ["professor_nova", "robo"], "location": None},
                1: {"characters": [], "location": None},
            },
        ), patch(
            "app.pipeline.default_pipeline.characters.get_character_reference",
            side_effect=lambda slug: registry_refs[slug],
        ):
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                character_selection=characters.AUTO_CHARACTER,
            )

        _, asset_gen_kwargs = self.started["asset_gen"].call_args
        self.assertEqual(
            asset_gen_kwargs["character_references_by_scene"],
            {0: [registry_refs["professor_nova"], registry_refs["robo"]], 1: []},
        )

    def test_elevenlabs_bgm_type_generates_music_and_overrides_render_bgm_file(self):
        # GÖREV 6 (gece oturumu): "elevenlabs" bgm_type, generate_bgm_from_
        # prompt()'u JIT çağırıp sonucunu bgm_file_override olarak
        # render_final_video()'ya geçiriyor -- video-to-music'in aksine,
        # video render'dan ÖNCE, tek geçişte (bkz. PROGRESS.md için neden).
        with patch.object(
            default_pipeline.elevenlabs_music,
            "generate_bgm_from_prompt",
            return_value="/tmp/tasks/proj-1/elevenlabs_bgm.mp3",
        ) as generate_music:
            project = default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                bgm_type="elevenlabs",
                bgm_volume=0.5,
                video_music_prompt="epic orchestral instrumental",
            )

        generate_music.assert_called_once()
        args = generate_music.call_args.args
        self.assertEqual(args[0], "epic orchestral instrumental")
        self.assertEqual(args[1], self.timeline.total_duration)
        self.assertEqual(project.video_music_prompt, "epic orchestral instrumental")

        _, video_kwargs = self.started["video"].call_args
        self.assertEqual(
            video_kwargs["bgm_file_override"], "/tmp/tasks/proj-1/elevenlabs_bgm.mp3"
        )

    def test_elevenlabs_bgm_failure_falls_back_to_no_override_without_crashing(self):
        with patch.object(
            default_pipeline.elevenlabs_music,
            "generate_bgm_from_prompt",
            side_effect=default_pipeline.elevenlabs_music.ElevenLabsMusicError(
                "quota exceeded"
            ),
        ) as generate_music:
            project = default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                bgm_type="elevenlabs",
                bgm_volume=0.5,
                video_music_prompt="epic orchestral instrumental",
            )

        generate_music.assert_called_once()
        self.assertEqual(project.final_video_path, "/tmp/tasks/proj-1/final.mp4")
        _, video_kwargs = self.started["video"].call_args
        self.assertIsNone(video_kwargs["bgm_file_override"])

    def test_non_elevenlabs_bgm_type_never_calls_elevenlabs_and_no_override(self):
        with patch.object(
            default_pipeline.elevenlabs_music, "generate_bgm_from_prompt"
        ) as generate_music:
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                bgm_type="random",
            )

        generate_music.assert_not_called()
        _, video_kwargs = self.started["video"].call_args
        self.assertIsNone(video_kwargs["bgm_file_override"])

    def test_elevenlabs_bgm_type_with_zero_volume_never_calls_elevenlabs(self):
        # should_use_bgm() güvenlik kısayolu -- provider'dan bağımsız,
        # random/custom/elevenlabs hepsi 0 hacimde atlanmalı.
        with patch.object(
            default_pipeline.elevenlabs_music, "generate_bgm_from_prompt"
        ) as generate_music:
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
                bgm_type="elevenlabs",
                bgm_volume=0.0,
                video_music_prompt="epic orchestral instrumental",
            )

        generate_music.assert_not_called()

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
        # No point extracting a second/third/fourth frame if the first one
        # already failed (no combined video to extract from any of them).
        self.started["thumbnail_b"].assert_not_called()
        self.started["thumbnail_c"].assert_not_called()
        self.started["thumbnail_d"].assert_not_called()
        self.assertEqual(project.thumbnail_variant_b_path, "")
        self.assertEqual(project.thumbnail_variant_c_path, "")
        self.assertEqual(project.thumbnail_variant_d_path, "")

    def test_saves_project_snapshot_to_disk_with_full_content(self):
        project = default_pipeline.run_pipeline(
            project_id="proj-1",
            topic="The Fall of Rome",
            language="auto",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
        )

        snapshot_path = os.path.join(utils.task_dir("proj-1"), "project.json")
        self.assertTrue(os.path.exists(snapshot_path))
        with open(snapshot_path, encoding="utf-8") as f:
            saved = json.load(f)

        self.assertEqual(saved["topic"], "The Fall of Rome")
        self.assertEqual(saved["final_video_path"], project.final_video_path)
        self.assertEqual(saved["thumbnail_path"], project.thumbnail_path)
        self.assertEqual(saved["thumbnail_variant_b_path"], project.thumbnail_variant_b_path)
        self.assertEqual(saved["thumbnail_variant_c_path"], project.thumbnail_variant_c_path)
        self.assertEqual(saved["thumbnail_variant_d_path"], project.thumbnail_variant_d_path)
        # The exact data the user actually needs for retroactive debugging:
        # per-scene storyboard search_terms and the downloaded asset paths.
        self.assertEqual(
            saved["storyboard"]["shots"][0]["search_terms"], ["ancient ruins"]
        )
        self.assertEqual(
            saved["asset_plan"]["downloaded_paths"], ["/tmp/ruins.mp4", "/tmp/battle.mp4"]
        )

    def test_snapshot_survives_on_disk_when_a_later_stage_raises(self):
        self.started["video"].side_effect = RuntimeError("render exploded")

        with self.assertRaises(RuntimeError):
            default_pipeline.run_pipeline(
                project_id="proj-1",
                topic="The Fall of Rome",
                language="auto",
                pacing=Pacing.short,
                voice_name="en-US-JennyNeural",
            )

        snapshot_path = os.path.join(utils.task_dir("proj-1"), "project.json")
        self.assertTrue(os.path.exists(snapshot_path))
        with open(snapshot_path, encoding="utf-8") as f:
            saved = json.load(f)

        # SEO (the stage right before the one that raised) made it to disk...
        self.assertEqual(saved["seo"]["title"], "The Fall of Rome")
        # ...but the video render itself never completed.
        self.assertEqual(saved["final_video_path"], "")


class TestRegenerateFromEditedScript(unittest.TestCase):
    """ÖZELLİK A (kullanıcı onaylı): tamamlanmış bir projenin script'i
    düzenlenip SADECE stage 9-12 (TTS/timeline/SEO/render) yeniden
    çalıştırılıyor -- storyboard/asset_plan (görseller) HİÇ dokunulmuyor.
    """

    def setUp(self):
        self.asset_plan = AssetPlan(
            candidates=[AssetCandidate(scene_index=0, search_term="ancient ruins")],
            downloaded_paths=["/tmp/ruins.mp4"],
        )
        self.research_plan = ResearchPlan(
            topic="The Fall of Rome",
            key_facts=["Rome was founded in 753 BC.", "The Senate governed the Republic."],
        )
        self.scene_plan = ScenePlan(
            pacing=Pacing.short,
            scenes=[Scene(index=0, title="Origins", narration_beat="How Rome began", duration_seconds=5.0)],
        )
        self.project = DocumentaryProject(
            project_id="proj-edit-1",
            topic="The Fall of Rome",
            language="en",
            pacing=Pacing.short,
            voice_name="en-US-JennyNeural",
            voice_rate=1.0,
            voice_volume=1.0,
            video_aspect="9:16",
            bgm_type="random",
            bgm_volume=0.3,
            research_plan=self.research_plan,
            scene_plan=self.scene_plan,
            script=Script(full_text="Original narration.", lines=[ScriptLine(scene_index=0, text="Original narration.")]),
            storyboard=Storyboard(shots=[StoryboardShot(scene_index=0, description="ruins")]),
            asset_plan=self.asset_plan,
            audio_plan=AudioPlan(
                narration=AudioTrack(voice_file="/tmp/old_audio.mp3", duration_seconds=5.0),
                bgm_file="/tmp/bgm.mp3",
            ),
            timeline=Timeline(combined_video_path="/tmp/old_combined.mp4", total_duration=5.0),
            seo=SeoMetadata(title="Old Title"),
            final_video_path="/tmp/old_final.mp4",
        )
        self.edited_script = Script(
            full_text="Edited narration.", lines=[ScriptLine(scene_index=0, text="Edited narration.")]
        )

        new_audio_plan = AudioPlan(
            narration=AudioTrack(voice_file="/tmp/new_audio.mp3", duration_seconds=6.0),
            bgm_file="/tmp/bgm.mp3",
        )
        new_timeline = Timeline(combined_video_path="/tmp/new_combined.mp4", total_duration=6.0)
        new_seo = SeoMetadata(title="New Title")

        self.mocks = {
            "audio": patch(
                "app.pipeline.default_pipeline.audio_renderer.render_audio_plan",
                return_value=new_audio_plan,
            ),
            "timeline": patch(
                "app.pipeline.default_pipeline.timeline_builder.build_timeline",
                return_value=new_timeline,
            ),
            "seo": patch(
                "app.pipeline.default_pipeline.seo_generator.generate_seo_metadata",
                return_value=new_seo,
            ),
            "video": patch(
                "app.pipeline.default_pipeline.video_renderer.render_final_video",
                return_value="/tmp/new_final.mp4",
            ),
            "video_params": patch(
                "app.pipeline.default_pipeline.video_renderer.build_video_params",
                return_value=object(),
            ),
            "quality": patch(
                "app.pipeline.default_pipeline.quality_critic.evaluate_project", return_value=None
            ),
            "thumbnail": patch(
                "app.pipeline.default_pipeline.thumbnail_generator.generate_thumbnail",
                return_value="/tmp/new_thumb.png",
            ),
            "thumbnail_b": patch(
                "app.pipeline.default_pipeline.thumbnail_generator.generate_thumbnail_variant_b",
                return_value="/tmp/new_thumb_b.png",
            ),
            "thumbnail_c": patch(
                "app.pipeline.default_pipeline.thumbnail_generator.generate_thumbnail_variant_c",
                return_value="/tmp/new_thumb_c.png",
            ),
            "thumbnail_d": patch(
                "app.pipeline.default_pipeline.thumbnail_generator.generate_thumbnail_variant_d",
                return_value="/tmp/new_thumb_d.png",
            ),
            # Görsel-üreten hiçbir aşama çağrılmamalı -- yanlışlıkla çağrılırsa
            # bu mock'lar hemen fırlatır, sessizce geçmez.
            "asset_gen": patch(
                "app.pipeline.default_pipeline.asset_generator.build_asset_plan",
                side_effect=AssertionError("asset_generator must not run on script edit"),
            ),
            "asset_dl": patch(
                "app.pipeline.default_pipeline.asset_downloader.download_assets",
                side_effect=AssertionError("asset_downloader must not run on script edit"),
            ),
            "ai_video": patch(
                "app.pipeline.default_pipeline.ai_video_generator.generate_ai_clips",
                side_effect=AssertionError("ai_video_generator must not run on script edit"),
            ),
            "storyboard": patch(
                "app.pipeline.default_pipeline.storyboard_generator.generate_storyboard",
                side_effect=AssertionError("storyboard_generator must not run on script edit"),
            ),
        }
        self.started = {name: m.start() for name, m in self.mocks.items()}
        for m in self.mocks.values():
            self.addCleanup(m.stop)
        self.addCleanup(lambda: shutil.rmtree(utils.task_dir("proj-edit-1"), ignore_errors=True))

    def test_replaces_script_and_reruns_only_audio_timeline_seo_video(self):
        result = default_pipeline.regenerate_from_edited_script(self.project, self.edited_script)

        self.assertIs(result, self.project)
        self.assertIs(result.script, self.edited_script)
        self.assertEqual(result.final_video_path, "/tmp/new_final.mp4")
        self.assertEqual(result.seo.title, "New Title")
        self.assertEqual(result.timeline.combined_video_path, "/tmp/new_combined.mp4")
        self.assertEqual(result.thumbnail_path, "/tmp/new_thumb.png")
        self.assertEqual(result.thumbnail_variant_b_path, "/tmp/new_thumb_b.png")
        self.assertEqual(result.thumbnail_variant_c_path, "/tmp/new_thumb_c.png")
        self.assertEqual(result.thumbnail_variant_d_path, "/tmp/new_thumb_d.png")

        self.started["asset_gen"].assert_not_called()
        self.started["asset_dl"].assert_not_called()
        self.started["ai_video"].assert_not_called()
        self.started["storyboard"].assert_not_called()

    def test_reuses_the_same_asset_plan_object_for_the_timeline(self):
        default_pipeline.regenerate_from_edited_script(self.project, self.edited_script)

        timeline_args, _ = self.started["timeline"].call_args
        self.assertIs(timeline_args[0], self.asset_plan)

    def test_passes_edited_script_to_audio_and_seo(self):
        default_pipeline.regenerate_from_edited_script(self.project, self.edited_script)

        audio_args, _ = self.started["audio"].call_args
        self.assertIs(audio_args[0], self.edited_script)
        seo_args, _ = self.started["seo"].call_args
        self.assertIs(seo_args[1], self.edited_script)

    def test_preserves_original_bgm_file_across_the_new_audio_plan(self):
        default_pipeline.regenerate_from_edited_script(self.project, self.edited_script)

        _, audio_kwargs = self.started["audio"].call_args
        self.assertEqual(audio_kwargs["bgm_file"], "/tmp/bgm.mp3")

    def test_preserves_original_character_references_across_the_new_audio_plan(self):
        # "Karakter Sesi" planı (kullanıcı onaylı): script düzenlendiğinde
        # ses YENİDEN üretiliyor -- karakter sesi de sessizce genel sese
        # DÜŞMEMELİ, orijinal projenin character_references'ı korunmalı.
        from app.models.character import CharacterReference

        bao = CharacterReference(name="Bao", frontal_image_url="data:image/jpeg;base64,x")
        self.project.character_references = [bao]

        default_pipeline.regenerate_from_edited_script(self.project, self.edited_script)

        _, audio_kwargs = self.started["audio"].call_args
        self.assertEqual(audio_kwargs["character_references"], [bao])

    def test_reuses_original_bgm_type_and_volume_for_video_params(self):
        default_pipeline.regenerate_from_edited_script(self.project, self.edited_script)

        _, params_kwargs = self.started["video_params"].call_args
        self.assertEqual(params_kwargs["bgm_type"], "random")
        self.assertEqual(params_kwargs["bgm_volume"], 0.3)

    def test_persists_the_final_state_to_disk(self):
        default_pipeline.regenerate_from_edited_script(self.project, self.edited_script)

        snapshot_path = os.path.join(utils.task_dir("proj-edit-1"), "project.json")
        with open(snapshot_path, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["script"]["full_text"], "Edited narration.")
        self.assertEqual(saved["final_video_path"], "/tmp/new_final.mp4")


if __name__ == "__main__":
    unittest.main()
