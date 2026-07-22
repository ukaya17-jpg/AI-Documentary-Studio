from pydantic import BaseModel, Field


class TimelineClip(BaseModel):
    scene_index: int
    video_path: str
    start: float = 0.0
    end: float = 0.0


class Timeline(BaseModel):
    clips: list[TimelineClip] = Field(default_factory=list)
    combined_video_path: str = ""
    total_duration: float = 0.0
