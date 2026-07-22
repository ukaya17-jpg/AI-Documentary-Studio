from pydantic import BaseModel, Field


class StoryboardShot(BaseModel):
    scene_index: int
    description: str = ""
    shot_type: str = ""
    search_terms: list[str] = Field(default_factory=list)


class Storyboard(BaseModel):
    shots: list[StoryboardShot] = Field(default_factory=list)
