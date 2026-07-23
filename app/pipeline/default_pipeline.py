"""Default AI Documentary Studio pipeline orchestrator.

Intent -> Research -> Outline -> Scene -> Script -> Storyboard -> Asset ->
AssetDownload -> Audio(TTS) -> Timeline -> SEO -> VideoRenderer
"""

import os

from loguru import logger

from app.config.profile_dimensions import (
    PACING_SCENE_SPEC,
    Pacing,
    Tone,
    TopicCategory,
    resolve_pacing,
    resolve_tone,
)
from app.models.documentary_project import DocumentaryProject
from app.models.schema import VideoAspect, VideoConcatMode
from app.departments.creative import scene_planner, script_generator, storyboard_generator
from app.departments.growth import seo_generator, thumbnail_generator
from app.departments.production import (
    asset_downloader,
    asset_generator,
    audio_renderer,
    timeline_builder,
    video_renderer,
)
from app.departments.research import intent_analyzer, outline_generator, research_planner
from app.thinking import quality_critic
from app.utils import utils

TOTAL_STAGES = 12


def _save_project_snapshot(project: DocumentaryProject) -> None:
    """Persist the current project state to storage/tasks/<id>/project.json.

    Plain pydantic serialization (model_dump_json()) -- no custom schema.
    Called after every stage so partial progress (each scene's storyboard
    search_terms, which asset was downloaded for it, timeline clip order,
    ...) survives on disk even if a later stage fails or the process is
    interrupted. Never raises: a disk-write failure must not abort the
    pipeline.
    """
    try:
        task_directory = utils.task_dir(project.project_id)
        snapshot_path = os.path.join(task_directory, "project.json")
        with open(snapshot_path, "w", encoding="utf-8") as f:
            f.write(project.model_dump_json(indent=2))
    except Exception as e:
        logger.warning(f"documentary pipeline: failed to save project snapshot: {e}")


def run_pipeline(
    project_id: str,
    topic: str,
    language: str = "auto",
    topic_category_override: TopicCategory | str | None = None,
    tone: Tone | str | None = None,
    pacing: Pacing | str = Pacing.short,
    voice_name: str = "",
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    video_source: str = "pexels",
    video_aspect: str = "9:16",
    bgm_type: str = "random",
    bgm_file: str = "",
    bgm_volume: float = 0.2,
) -> DocumentaryProject:
    resolved_pacing = resolve_pacing(pacing)
    project = DocumentaryProject(
        project_id=project_id,
        topic=topic,
        language=language,
        pacing=resolved_pacing,
        voice_name=voice_name,
        voice_rate=voice_rate,
        voice_volume=voice_volume,
        video_source=video_source,
        video_aspect=video_aspect,
    )

    def stage(n: int, name: str):
        logger.info(f"documentary pipeline [{n}/{TOTAL_STAGES}] {name}: {topic}")

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
        _save_project_snapshot(project)

        stage(2, "research")
        project.research_plan = research_planner.generate_research_plan(
            topic, tone=resolved_tone, language=project.language
        )
        _save_project_snapshot(project)

        stage(3, "outline")
        project.outline = outline_generator.generate_outline(
            topic,
            research_plan=project.research_plan,
            tone=resolved_tone,
            language=project.language,
        )
        _save_project_snapshot(project)

        stage(4, "scene")
        project.scene_plan = scene_planner.plan_scenes(project.outline, pacing=resolved_pacing)
        _save_project_snapshot(project)

        stage(5, "script")
        project.script = script_generator.generate_script(
            project.scene_plan,
            topic,
            language=project.language,
            outline=project.outline,
            tone=resolved_tone,
        )
        _save_project_snapshot(project)

        stage(6, "storyboard")
        project.storyboard = storyboard_generator.generate_storyboard(
            project.scene_plan,
            project.script,
            topic_category=project.topic_category,
            topic=project.topic,
            key_facts=project.research_plan.key_facts[:3],
        )
        _save_project_snapshot(project)

        stage(7, "asset")
        project.asset_plan = asset_generator.build_asset_plan(project.storyboard, provider=video_source)
        _save_project_snapshot(project)

        stage(8, "asset download")
        aspect_enum = VideoAspect(video_aspect)
        max_clip_duration = int(PACING_SCENE_SPEC[resolved_pacing]["scene_duration"])
        # TTS hasn't run yet at this point, so the scene duration budget is used as
        # the audio-duration estimate for how much footage to fetch.
        project.asset_plan = asset_downloader.download_assets(
            project.asset_plan,
            task_id=project.project_id,
            audio_duration=project.scene_plan.total_duration,
            video_source=video_source,
            video_aspect=aspect_enum,
            video_concat_mode=VideoConcatMode.random,
            max_clip_duration=max_clip_duration,
        )
        _save_project_snapshot(project)

        stage(9, "audio (TTS)")
        project.audio_plan = audio_renderer.render_audio_plan(
            project.script,
            task_id=project.project_id,
            voice_name=voice_name,
            voice_rate=voice_rate,
            voice_volume=voice_volume,
            bgm_file=bgm_file,
        )
        _save_project_snapshot(project)

        stage(10, "timeline")
        project.timeline = timeline_builder.build_timeline(
            project.asset_plan,
            project.audio_plan.narration,
            task_id=project.project_id,
            video_aspect=aspect_enum,
            video_concat_mode=VideoConcatMode.random,
            max_clip_duration=max_clip_duration,
        )
        _save_project_snapshot(project)

        stage(11, "seo")
        project.seo = seo_generator.generate_seo_metadata(
            topic, project.script, language=project.language, scene_plan=project.scene_plan
        )
        _save_project_snapshot(project)

        stage(12, "video render")
        params = video_renderer.build_video_params(
            topic=topic,
            video_aspect=video_aspect,
            voice_name=voice_name,
            bgm_type=bgm_type,
            bgm_file=bgm_file,
            bgm_volume=bgm_volume,
        )
        project.final_video_path = video_renderer.render_final_video(
            project.timeline,
            project.audio_plan.narration,
            task_id=project.project_id,
            params=params,
        )
        _save_project_snapshot(project)

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
        _save_project_snapshot(project)

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

        logger.success(f"documentary pipeline done: {project.final_video_path}")
        return project
    finally:
        # Guarantees a snapshot reflecting wherever the project got to, even
        # if a stage above raised -- "success or failure, doesn't matter".
        _save_project_snapshot(project)
