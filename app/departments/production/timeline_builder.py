"""Timeline stage: concatenate downloaded assets against the narration track.

Thin wrapper around the legacy app.services.video combine_videos(), reused
as-is, not reimplemented.
"""

import os

from app.models.asset import AssetPlan
from app.models.audio import AudioTrack
from app.models.schema import VideoAspect, VideoConcatMode, VideoTransitionMode
from app.models.timeline import Timeline, TimelineClip
from app.services import video
from app.utils import utils


def build_timeline(
    asset_plan: AssetPlan,
    audio_track: AudioTrack,
    task_id: str,
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_concat_mode: VideoConcatMode = VideoConcatMode.random,
    video_transition_mode: VideoTransitionMode | None = None,
    max_clip_duration: int = 5,
    threads: int = 2,
    clip_speed: float = 1.0,
) -> Timeline:
    task_directory = utils.task_dir(task_id)
    combined_video_path = os.path.join(task_directory, "combined.mp4")

    video.combine_videos(
        combined_video_path=combined_video_path,
        video_paths=asset_plan.downloaded_paths,
        audio_file=audio_track.voice_file,
        video_aspect=video_aspect,
        video_concat_mode=video_concat_mode,
        video_transition_mode=video_transition_mode,
        max_clip_duration=max_clip_duration,
        threads=threads,
        clip_speed=clip_speed,
    )

    # combine_videos may loop/reorder/drop clips internally to fill the audio
    # duration, so this scene<->path pairing is best-effort bookkeeping, not
    # an exact reconstruction of what ended up in the merged file.
    clips = [
        TimelineClip(scene_index=candidate.scene_index, video_path=path)
        for candidate, path in zip(asset_plan.candidates, asset_plan.downloaded_paths)
    ]
    return Timeline(
        clips=clips,
        combined_video_path=combined_video_path,
        total_duration=audio_track.duration_seconds,
    )
