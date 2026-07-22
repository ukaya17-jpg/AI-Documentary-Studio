"""AssetDownload stage: fetch stock footage for a planned search list.

Thin wrapper around the legacy app.services.material download pipeline
(Pexels/Pixabay/Coverr) -- reused as-is, not reimplemented.
"""

from app.models.asset import AssetPlan
from app.models.schema import VideoAspect, VideoConcatMode
from app.services import material


def download_assets(
    asset_plan: AssetPlan,
    task_id: str,
    audio_duration: float,
    video_source: str = "pexels",
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_concat_mode: VideoConcatMode = VideoConcatMode.random,
    max_clip_duration: int = 5,
) -> AssetPlan:
    search_terms = [c.search_term for c in asset_plan.candidates if c.search_term]
    if not search_terms:
        return asset_plan

    asset_plan.downloaded_paths = material.download_videos(
        task_id=task_id,
        search_terms=search_terms,
        source=video_source,
        video_aspect=video_aspect,
        video_concat_mode=video_concat_mode,
        audio_duration=audio_duration,
        max_clip_duration=max_clip_duration,
        # Candidates are already in scene/narrative order (one per storyboard
        # shot), so this keeps downloaded footage aligned with the timeline.
        match_script_order=True,
    )
    return asset_plan
