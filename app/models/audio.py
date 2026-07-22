from pydantic import BaseModel


class AudioTrack(BaseModel):
    voice_name: str = ""
    voice_file: str = ""
    subtitle_file: str = ""
    duration_seconds: float = 0.0


class AudioPlan(BaseModel):
    narration: AudioTrack | None = None
    bgm_file: str = ""
