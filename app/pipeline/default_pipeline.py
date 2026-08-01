"""Default AI Documentary Studio pipeline orchestrator.

Intent -> Research -> Outline -> Scene -> Script -> Storyboard -> Asset ->
AssetDownload -> Audio(TTS) -> Timeline -> SEO -> VideoRenderer
"""

import os
from typing import Callable

from loguru import logger

from app.config.profile_dimensions import (
    PACING_SCENE_SPEC,
    Format,
    Pacing,
    Tone,
    TopicCategory,
    resolve_format,
    resolve_pacing,
    resolve_tone,
)
from app.models.character import CharacterReference
from app.models.documentary_project import DocumentaryProject
from app.models.schema import VideoAspect, VideoConcatMode
from app.models.script import Script
from app.departments.creative import scene_planner, script_generator, storyboard_generator
from app.departments.growth import seo_generator, thumbnail_generator
from app.departments.production import (
    ai_video_generator,
    asset_downloader,
    asset_generator,
    audio_renderer,
    timeline_builder,
    video_renderer,
)
from app.departments.research import intent_analyzer, outline_generator, research_planner
from app.services import bgm as bgm_service
from app.services import elevenlabs_music
from app.thinking import quality_critic
from app.utils import utils

TOTAL_STAGES = 12

# OTONOM KARAR (gece oturumu, GÖREV 1a): asset download (stage 8) runs before
# TTS (stage 9), so it has to estimate how much footage it'll need from
# scene_plan.total_duration (the *target* scene durations) rather than the
# real rendered narration length. Measured on a real run: script_generator's
# target was 48 words (4 scenes x 12 words @ _WORDS_PER_SECOND=2.3) but the
# LLM produced 78 (+62%), and the real TTS audio came out to 40.39s against a
# 20.0s scene_plan.total_duration estimate (2.02x). When downloaded footage
# falls short of the real audio length, video.combine_videos() pads the gap
# by cycling through already-used clips -- this is the repeated-frame bug.
# Conservative, reversible fix: over-fetch footage against a safety-padded
# duration estimate instead of the raw (frequently-undershot) scene total.
# Worst case if this is too generous is a few extra free Pexels downloads.
_ASSET_DOWNLOAD_DURATION_SAFETY_MULTIPLIER = 2.0

# Real-money AI-generated video clips (fal.ai/Kling) -- opt-in only, must be
# explicitly selected via video_source, default stock behavior (pexels/
# pixabay/coverr/local) is completely unaffected. See PROGRESS.md for the
# full architectural rationale from planning.
AI_GENERATED_VIDEO_SOURCE = "ai_generated"


def run_pipeline(
    project_id: str,
    topic: str,
    language: str = "auto",
    topic_category_override: TopicCategory | str | None = None,
    tone: Tone | str | None = None,
    format: Format | str | None = None,
    pacing: Pacing | str = Pacing.short,
    voice_name: str = "",
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    video_source: str = "pexels",
    video_aspect: str = "9:16",
    bgm_type: str = "random",
    bgm_file: str = "",
    bgm_volume: float = 0.2,
    video_music_prompt: str = "",
    custom_system_prompt: str = "",
    custom_requirements: str = "",
    character_reference: CharacterReference | None = None,
    on_stage_change: Callable[[int, str], None] | None = None,
    on_substage_progress: Callable[[int, int], None] | None = None,
) -> DocumentaryProject:
    """Run the full Intent->...->VideoRenderer pipeline for one documentary.

    `on_stage_change`, if given, is called as `on_stage_change(n, name)` at
    the start of each of the 12 stages (same `n`/`name` as the `stage()`
    log line below) -- purely additive, e.g. for a caller (webui) to drive a
    live progress indicator. `None` (the default) preserves every existing
    caller's behavior exactly: this hook does not change what the pipeline
    does, only what it reports while doing it.

    `on_substage_progress`, if given, is called as
    `on_substage_progress(completed, total)` during stage 8 ONLY when
    `video_source` is `AI_GENERATED_VIDEO_SOURCE` -- a single stage-level
    message ("asset download") isn't enough feedback when that stage can
    take many minutes (each AI clip takes ~6min to generate). Unused (never
    called) for every stock video_source, exactly like on_stage_change,
    `None` changes nothing.

    `character_reference`, if given, is threaded straight into stage 7
    (asset_generator.build_asset_plan, for the "@Element1" prompt prefix)
    and stage 8 (ai_video_generator.generate_ai_clips, for the actual
    Kling O1 API call) -- see docs/character-consistency-research.md. It is
    orthogonal to `format`/`Format.kids`: a character-consistent project is
    not required to also be kids-safe, and vice versa (same relationship as
    `tone`/`format`).
    """
    resolved_pacing = resolve_pacing(pacing)
    # Unlike tone, format doesn't depend on topic_category -- it can be
    # resolved up front alongside pacing, no need to wait for stage 1.
    resolved_format = resolve_format(format)
    project = DocumentaryProject(
        project_id=project_id,
        topic=topic,
        language=language,
        format=resolved_format,
        pacing=resolved_pacing,
        voice_name=voice_name,
        voice_rate=voice_rate,
        voice_volume=voice_volume,
        video_source=video_source,
        video_aspect=video_aspect,
        bgm_type=bgm_type,
        bgm_volume=bgm_volume,
        video_music_prompt=video_music_prompt,
        custom_system_prompt=custom_system_prompt,
        custom_requirements=custom_requirements,
        character_reference=character_reference,
    )

    def stage(n: int, name: str):
        logger.info(f"documentary pipeline [{n}/{TOTAL_STAGES}] {name}: {topic}")
        if on_stage_change is not None:
            on_stage_change(n, name)

    try:
        stage(1, "intent")
        intent = intent_analyzer.analyze_intent(
            topic, language=language, topic_category_override=topic_category_override
        )
        project.language = intent["language"]
        project.topic_category = intent["topic_category"]
        # Tone resolution depends on topic_category, which is only known
        # after intent analysis -- can't be resolved alongside resolved_pacing
        # up front. With no override, this reproduces each category's old
        # hard-locked tone exactly (see resolve_tone/DEFAULT_TONE_BY_CATEGORY).
        resolved_tone = resolve_tone(project.topic_category, tone)
        project.tone = resolved_tone
        utils.save_project_snapshot(project)

        stage(2, "research")
        project.research_plan = research_planner.generate_research_plan(
            topic,
            tone=resolved_tone,
            language=project.language,
            topic_category=project.topic_category,
        )
        utils.save_project_snapshot(project)

        stage(3, "outline")
        project.outline = outline_generator.generate_outline(
            topic,
            research_plan=project.research_plan,
            tone=resolved_tone,
            language=project.language,
            pacing=resolved_pacing,
        )
        utils.save_project_snapshot(project)

        stage(4, "scene")
        project.scene_plan = scene_planner.plan_scenes(project.outline, pacing=resolved_pacing)
        utils.save_project_snapshot(project)

        stage(5, "script")
        project.script = script_generator.generate_script(
            project.scene_plan,
            topic,
            language=project.language,
            custom_system_prompt=custom_system_prompt,
            outline=project.outline,
            tone=resolved_tone,
            format=resolved_format,
            custom_requirements=custom_requirements,
        )
        utils.save_project_snapshot(project)

        stage(6, "storyboard")
        project.storyboard = storyboard_generator.generate_storyboard(
            project.scene_plan,
            project.script,
            topic_category=project.topic_category,
            topic=project.topic,
            key_facts=project.research_plan.key_facts[:3],
        )
        utils.save_project_snapshot(project)

        stage(7, "asset")
        project.asset_plan = asset_generator.build_asset_plan(
            project.storyboard,
            provider=video_source,
            topic_category=project.topic_category,
            script=project.script,
            character_reference=character_reference,
        )
        utils.save_project_snapshot(project)

        stage(8, "asset download")
        aspect_enum = VideoAspect(video_aspect)
        max_clip_duration = int(PACING_SCENE_SPEC[resolved_pacing]["scene_duration"])
        if video_source == AI_GENERATED_VIDEO_SOURCE:
            project.asset_plan = ai_video_generator.generate_ai_clips(
                project.asset_plan,
                task_id=project.project_id,
                aspect_ratio=video_aspect,
                character_reference=character_reference,
                on_substage_progress=on_substage_progress,
            )
        else:
            # TTS hasn't run yet at this point, so the scene duration budget is used as
            # the audio-duration estimate for how much footage to fetch -- padded by
            # _ASSET_DOWNLOAD_DURATION_SAFETY_MULTIPLIER since real narration audio
            # commonly runs much longer than this estimate (see the constant's
            # docstring above for the measured numbers).
            estimated_footage_duration = (
                project.scene_plan.total_duration * _ASSET_DOWNLOAD_DURATION_SAFETY_MULTIPLIER
            )
            project.asset_plan = asset_downloader.download_assets(
                project.asset_plan,
                task_id=project.project_id,
                audio_duration=estimated_footage_duration,
                video_source=video_source,
                video_aspect=aspect_enum,
                video_concat_mode=VideoConcatMode.random,
                max_clip_duration=max_clip_duration,
            )
        utils.save_project_snapshot(project)

        stage(9, "audio (TTS)")
        project.audio_plan = audio_renderer.render_audio_plan(
            project.script,
            task_id=project.project_id,
            voice_name=voice_name,
            voice_rate=voice_rate,
            voice_volume=voice_volume,
            bgm_file=bgm_file,
        )
        utils.save_project_snapshot(project)

        stage(10, "timeline")
        project.timeline = timeline_builder.build_timeline(
            project.asset_plan,
            project.audio_plan.narration,
            task_id=project.project_id,
            video_aspect=aspect_enum,
            video_concat_mode=VideoConcatMode.random,
            max_clip_duration=max_clip_duration,
        )
        utils.save_project_snapshot(project)

        stage(11, "seo")
        project.seo = seo_generator.generate_seo_metadata(
            topic,
            project.script,
            language=project.language,
            scene_plan=project.scene_plan,
            key_facts=project.research_plan.key_facts[:3],
        )
        utils.save_project_snapshot(project)

        stage(12, "video render")
        params = video_renderer.build_video_params(
            topic=topic,
            video_aspect=video_aspect,
            voice_name=voice_name,
            bgm_type=bgm_type,
            bgm_file=bgm_file,
            bgm_volume=bgm_volume,
        )
        # GÖREV 6 (gece oturumu): ElevenLabs, "random"/"custom" gibi hazır bir
        # dosyaya değil, gerçek zamanlı üretime dayanıyor -- bu yüzden
        # get_bgm_file()'ın (video.py) çözümleyebileceği bir bgm_file yerine,
        # burada JIT üretilip bgm_file_override olarak geçiriliyor (Classic
        # Mode'un Sonilo/ElevenLabs için zaten kullandığı AYNI mekanizma).
        # Üretim başarısız olursa pipeline ÇÖKMÜYOR -- narrasyon-only final
        # video ile devam ediyor (get_bgm_file()'ın "no files found" ile
        # zaten yaptığı sessiz düşüş ile aynı tolerans).
        elevenlabs_bgm_file = None
        if bgm_type == "elevenlabs" and bgm_service.should_use_bgm(bgm_type, bgm_volume):
            try:
                elevenlabs_bgm_file = elevenlabs_music.generate_bgm_from_prompt(
                    video_music_prompt,
                    project.timeline.total_duration,
                    os.path.join(utils.task_dir(project.project_id), "elevenlabs_bgm.mp3"),
                )
            except elevenlabs_music.ElevenLabsMusicError as e:
                logger.warning(
                    f"documentary pipeline: ElevenLabs background music generation "
                    f"failed, continuing without BGM: {e}"
                )
        project.final_video_path = video_renderer.render_final_video(
            project.timeline,
            project.audio_plan.narration,
            task_id=project.project_id,
            params=params,
            bgm_file_override=elevenlabs_bgm_file,
        )
        utils.save_project_snapshot(project)

        # Informational only: never blocks, never affects final_video_path.
        # What a failing verdict should actually do (retry a stage, warn the
        # user more loudly, ...) is a separate decision deferred until there's
        # real usage data -- see PROGRESS.md.
        project.quality_verdict = quality_critic.evaluate_project(project)
        if project.quality_verdict is not None:
            logger.info(
                f"documentary pipeline: quality verdict -- overall={project.quality_verdict.overall_score}, "
                f"passed={project.quality_verdict.passed}"
            )
            for issue in project.quality_verdict.issues:
                logger.info(f"documentary pipeline: quality issue -- {issue}")
        else:
            logger.warning(
                "documentary pipeline: quality review unavailable, continuing without a verdict"
            )
        utils.save_project_snapshot(project)

        # Best-effort only: a missing thumbnail never blocks or fails the pipeline.
        project.thumbnail_path = thumbnail_generator.generate_thumbnail(
            project.timeline.combined_video_path, project.seo, project.project_id
        )
        if project.thumbnail_path:
            logger.info(f"documentary pipeline: thumbnail generated -- {project.thumbnail_path}")
        else:
            logger.warning(
                "documentary pipeline: thumbnail generation unavailable, continuing without one"
            )

        # Second option for a quick A/B compare -- best-effort like the first,
        # never blocks. Only attempted if the first succeeded (no combined
        # video means no frame to extract from either).
        if project.thumbnail_path:
            project.thumbnail_variant_b_path = thumbnail_generator.generate_thumbnail_variant_b(
                project.timeline.combined_video_path, project.seo, project.project_id
            )

        logger.success(f"documentary pipeline done: {project.final_video_path}")
        return project
    finally:
        # Guarantees a snapshot reflecting wherever the project got to, even
        # if a stage above raised -- "success or failure, doesn't matter".
        utils.save_project_snapshot(project)


def regenerate_from_edited_script(
    project: DocumentaryProject, edited_script: Script
) -> DocumentaryProject:
    """Re-render audio/timeline/SEO/video for an ALREADY-COMPLETED project
    after the user edits its narration text (ÖZELLİK A, kullanıcı onaylı).

    Deliberately does NOT touch project.storyboard/project.asset_plan --
    visuals are never regenerated here (no new stock download, no new
    AI-video generation call, so this never costs real money even when
    video_source is the paid AI provider). Only stages 9 (TTS) through 12
    (video render) re-run, against the edited script, reusing whatever
    footage the original run already has. quality_critic and the two
    thumbnails are also refreshed (both cheap/free, and both would
    otherwise silently go stale -- the thumbnail overlays the OLD seo.title
    on a frame from the just-rebuilt combined.mp4).

    This is why editing is intended for wording fixes, not large content
    rewrites: if the edited narration's real spoken length diverges a lot
    from the original, the reused footage may no longer cover it well
    (the same repeated-frame/truncation risk documented elsewhere in this
    pipeline) -- the webui surfaces this as a caption, not a hard block.

    Raises whatever the underlying stage raises (e.g. TTS failure) --
    this is a user-triggered, foreground action, not a best-effort
    background one, so silently swallowing an error here would hide a
    real failure from the person who just clicked "regenerate".

    Mutates and returns `project` (same object); the caller persists it
    (see app.utils.utils.save_project_snapshot) exactly like run_pipeline().
    """
    existing_bgm_file = project.audio_plan.bgm_file if project.audio_plan else ""
    project.script = edited_script

    aspect_enum = VideoAspect(project.video_aspect)
    max_clip_duration = int(PACING_SCENE_SPEC[project.pacing]["scene_duration"])

    project.audio_plan = audio_renderer.render_audio_plan(
        project.script,
        task_id=project.project_id,
        voice_name=project.voice_name,
        voice_rate=project.voice_rate,
        voice_volume=project.voice_volume,
        bgm_file=existing_bgm_file,
    )
    utils.save_project_snapshot(project)

    project.timeline = timeline_builder.build_timeline(
        project.asset_plan,
        project.audio_plan.narration,
        task_id=project.project_id,
        video_aspect=aspect_enum,
        video_concat_mode=VideoConcatMode.random,
        max_clip_duration=max_clip_duration,
    )
    utils.save_project_snapshot(project)

    project.seo = seo_generator.generate_seo_metadata(
        project.topic,
        project.script,
        language=project.language,
        scene_plan=project.scene_plan,
        key_facts=project.research_plan.key_facts[:3] if project.research_plan else [],
    )
    utils.save_project_snapshot(project)

    params = video_renderer.build_video_params(
        topic=project.topic,
        video_aspect=project.video_aspect,
        voice_name=project.voice_name,
        bgm_type=project.bgm_type,
        bgm_file=existing_bgm_file,
        bgm_volume=project.bgm_volume,
    )
    # GÖREV 6: ElevenLabs BGM'i bir dosya olarak saklanmıyor (run_pipeline()
    # ile aynı gerekçe) -- project.video_music_prompt'tan yeniden üretiliyor.
    elevenlabs_bgm_file = None
    if project.bgm_type == "elevenlabs" and bgm_service.should_use_bgm(
        project.bgm_type, project.bgm_volume
    ):
        try:
            elevenlabs_bgm_file = elevenlabs_music.generate_bgm_from_prompt(
                project.video_music_prompt,
                project.timeline.total_duration,
                os.path.join(utils.task_dir(project.project_id), "elevenlabs_bgm.mp3"),
            )
        except elevenlabs_music.ElevenLabsMusicError as e:
            logger.warning(
                f"documentary pipeline (regenerate): ElevenLabs background "
                f"music generation failed, continuing without BGM: {e}"
            )
    project.final_video_path = video_renderer.render_final_video(
        project.timeline,
        project.audio_plan.narration,
        task_id=project.project_id,
        params=params,
        bgm_file_override=elevenlabs_bgm_file,
    )
    utils.save_project_snapshot(project)

    project.quality_verdict = quality_critic.evaluate_project(project)
    project.thumbnail_path = thumbnail_generator.generate_thumbnail(
        project.timeline.combined_video_path, project.seo, project.project_id
    )
    if project.thumbnail_path:
        project.thumbnail_variant_b_path = thumbnail_generator.generate_thumbnail_variant_b(
            project.timeline.combined_video_path, project.seo, project.project_id
        )
    utils.save_project_snapshot(project)

    logger.success(f"documentary pipeline: regenerated from edited script -- {project.final_video_path}")
    return project
