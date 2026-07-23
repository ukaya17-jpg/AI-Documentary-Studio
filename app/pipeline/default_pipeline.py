"""Default AI Documentary Studio pipeline orchestrator.

Intent -> Research -> Outline -> Scene -> Script -> Storyboard -> Asset ->
AssetDownload -> Audio(TTS) -> Timeline -> SEO -> VideoRenderer
"""

from loguru import logger

from app.config.profile_dimensions import PACING_SCENE_SPEC, Pacing, TopicCategory, resolve_pacing
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

TOTAL_STAGES = 12


def run_pipeline(
    project_id: str,
    topic: str,
    language: str = "auto",
    topic_category_override: TopicCategory | str | None = None,
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

    stage(1, "intent")
    intent = intent_analyzer.analyze_intent(
        topic, language=language, topic_category_override=topic_category_override
    )
    project.language = intent["language"]
    project.topic_category = intent["topic_category"]

    stage(2, "research")
    project.research_plan = research_planner.generate_research_plan(
        topic, topic_category=project.topic_category, language=project.language
    )

    stage(3, "outline")
    project.outline = outline_generator.generate_outline(
        topic,
        research_plan=project.research_plan,
        topic_category=project.topic_category,
        language=project.language,
    )

    stage(4, "scene")
    project.scene_plan = scene_planner.plan_scenes(project.outline, pacing=resolved_pacing)

    stage(5, "script")
    project.script = script_generator.generate_script(
        project.scene_plan, topic, language=project.language, outline=project.outline
    )

    stage(6, "storyboard")
    project.storyboard = storyboard_generator.generate_storyboard(
        project.scene_plan,
        project.script,
        topic_category=project.topic_category,
        topic=project.topic,
        key_facts=project.research_plan.key_facts[:3],
    )

    stage(7, "asset")
    project.asset_plan = asset_generator.build_asset_plan(project.storyboard, provider=video_source)

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

    stage(9, "audio (TTS)")
    project.audio_plan = audio_renderer.render_audio_plan(
        project.script,
        task_id=project.project_id,
        voice_name=voice_name,
        voice_rate=voice_rate,
        voice_volume=voice_volume,
        bgm_file=bgm_file,
    )

    stage(10, "timeline")
    project.timeline = timeline_builder.build_timeline(
        project.asset_plan,
        project.audio_plan.narration,
        task_id=project.project_id,
        video_aspect=aspect_enum,
        video_concat_mode=VideoConcatMode.random,
        max_clip_duration=max_clip_duration,
    )

    stage(11, "seo")
    project.seo = seo_generator.generate_seo_metadata(
        topic, project.script, language=project.language, scene_plan=project.scene_plan
    )

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
