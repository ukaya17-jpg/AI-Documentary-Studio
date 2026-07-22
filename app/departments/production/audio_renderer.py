"""Audio (TTS) stage: synthesize narration and a matching subtitle file.

Thin wrapper around the legacy app.services.voice tts()/create_subtitle(),
reused as-is, not reimplemented.
"""

import os

from app.models.audio import AudioPlan, AudioTrack
from app.models.script import Script
from app.services import voice
from app.utils import utils


def render_narration(
    script: Script,
    task_id: str,
    voice_name: str,
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
) -> AudioTrack:
    task_directory = utils.task_dir(task_id)
    audio_file = os.path.join(task_directory, "audio.mp3")
    subtitle_file = os.path.join(task_directory, "subtitle.srt")

    sub_maker = voice.tts(
        text=script.full_text,
        voice_name=voice.parse_voice_name(voice_name),
        voice_rate=voice_rate,
        voice_file=audio_file,
        voice_volume=voice_volume,
    )
    if sub_maker is None:
        raise RuntimeError(
            "failed to synthesize narration audio; check the selected voice and TTS connectivity"
        )

    duration_seconds = voice.get_audio_duration(sub_maker)
    voice.create_subtitle(sub_maker, script.full_text, subtitle_file)

    return AudioTrack(
        voice_name=voice_name,
        voice_file=audio_file,
        subtitle_file=subtitle_file if os.path.exists(subtitle_file) else "",
        duration_seconds=duration_seconds,
    )


def render_audio_plan(
    script: Script,
    task_id: str,
    voice_name: str,
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    bgm_file: str = "",
) -> AudioPlan:
    narration = render_narration(script, task_id, voice_name, voice_rate, voice_volume)
    return AudioPlan(narration=narration, bgm_file=bgm_file)
