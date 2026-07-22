"""VideoRenderer stage: final composite render (footage + narration + subtitles + BGM).

Thin wrapper around the legacy app.services.video generate_video(), reused
as-is, not reimplemented. The +faststart fix lives in generate_video()
itself so every caller (legacy task pipeline and this one) benefits.
"""

import os

from loguru import logger

from app.models.audio import AudioTrack
from app.models.schema import VideoParams
from app.models.timeline import Timeline
from app.services import video
from app.utils import utils


def render_final_video(
    timeline: Timeline,
    audio_track: AudioTrack,
    task_id: str,
    params: VideoParams,
) -> str:
    task_directory = utils.task_dir(task_id)
    output_file = os.path.join(task_directory, "final.mp4")

    bgm_mix_succeeded = video.generate_video(
        video_path=timeline.combined_video_path,
        audio_path=audio_track.voice_file,
        subtitle_path=audio_track.subtitle_file,
        output_file=output_file,
        params=params,
    )
    if not bgm_mix_succeeded and params.bgm_type and params.bgm_type != "none":
        logger.warning(
            f"video_renderer: BGM mix failed for task {task_id}, "
            "final video was written with narration only"
        )
    return output_file
