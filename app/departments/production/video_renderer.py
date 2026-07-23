"""VideoRenderer stage: final composite render (footage + narration + subtitles + BGM).

Thin wrapper around the legacy app.services.video generate_video(), reused
as-is, not reimplemented. The +faststart fix lives in generate_video()
itself so every caller (legacy task pipeline and this one) benefits.
"""

import os

from loguru import logger

from app.config import config
from app.models.audio import AudioTrack
from app.models.schema import VideoParams
from app.models.timeline import Timeline
from app.services import video
from app.utils import utils

# Mirrors webui/Main.py's DEFAULT_SUBTITLE_SETTINGS (both now default
# font_name to the same plain sans-serif, BeVietnamPro-Bold.ttf -- see
# GÖREV 8a in PROGRESS.md for why the two used to diverge). Duplicated here
# (rather than imported) because webui/Main.py runs `_render_application()`
# at import time and isn't safe to import from a non-Streamlit process.
_DEFAULT_SUBTITLE_SETTINGS = {
    "font_name": "BeVietnamPro-Bold.ttf",
    "subtitle_position": "bottom",
    "custom_position": 70.0,
    "text_fore_color": "#FFFFFF",
    "font_size": 60,
    "stroke_color": "#000000",
    "stroke_width": 1.5,
    "subtitle_background_enabled": False,
    "subtitle_background_color": "#000000",
    "rounded_subtitle_background": False,
}


def build_video_params(
    topic: str,
    video_aspect: str,
    voice_name: str,
    bgm_type: str = "random",
    bgm_file: str = "",
    bgm_volume: float = 0.2,
) -> VideoParams:
    """Build render params honoring the user's configured subtitle appearance
    (config.toml [ui]) instead of the VideoParams schema's raw defaults --
    mirrors what the legacy WebUI form does when it saves widget values onto
    VideoParams before calling generate_video()."""
    subtitle_background_enabled = config.ui.get(
        "subtitle_background_enabled",
        _DEFAULT_SUBTITLE_SETTINGS["subtitle_background_enabled"],
    )
    text_background_color = (
        config.ui.get(
            "subtitle_background_color",
            _DEFAULT_SUBTITLE_SETTINGS["subtitle_background_color"],
        )
        if subtitle_background_enabled
        else False
    )
    return VideoParams(
        video_subject=topic,
        video_aspect=video_aspect,
        voice_name=voice_name,
        bgm_type=bgm_type,
        bgm_file=bgm_file,
        bgm_volume=bgm_volume,
        subtitle_enabled=True,
        font_name=config.ui.get("font_name", _DEFAULT_SUBTITLE_SETTINGS["font_name"]),
        subtitle_position=config.ui.get(
            "subtitle_position", _DEFAULT_SUBTITLE_SETTINGS["subtitle_position"]
        ),
        custom_position=config.ui.get(
            "custom_position", _DEFAULT_SUBTITLE_SETTINGS["custom_position"]
        ),
        text_fore_color=config.ui.get(
            "text_fore_color", _DEFAULT_SUBTITLE_SETTINGS["text_fore_color"]
        ),
        font_size=config.ui.get("font_size", _DEFAULT_SUBTITLE_SETTINGS["font_size"]),
        stroke_color=config.ui.get(
            "stroke_color", _DEFAULT_SUBTITLE_SETTINGS["stroke_color"]
        ),
        stroke_width=config.ui.get(
            "stroke_width", _DEFAULT_SUBTITLE_SETTINGS["stroke_width"]
        ),
        text_background_color=text_background_color,
        rounded_subtitle_background=config.ui.get(
            "rounded_subtitle_background",
            _DEFAULT_SUBTITLE_SETTINGS["rounded_subtitle_background"],
        ),
    )


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
