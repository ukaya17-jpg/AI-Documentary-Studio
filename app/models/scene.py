from pydantic import BaseModel, Field

from app.config.profile_dimensions import Pacing


class Scene(BaseModel):
    index: int
    title: str
    narration_beat: str = ""
    visual_keywords: list[str] = Field(default_factory=list)
    duration_seconds: float = 5.0
    importance: int = Field(default=3, ge=1, le=5)


class ScenePlan(BaseModel):
    pacing: Pacing = Pacing.short
    scenes: list[Scene] = Field(default_factory=list)

    @property
    def total_duration(self) -> float:
        return sum(scene.duration_seconds for scene in self.scenes)
