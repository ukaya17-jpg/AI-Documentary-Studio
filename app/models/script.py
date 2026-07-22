from pydantic import BaseModel, Field


class ScriptLine(BaseModel):
    scene_index: int
    text: str


class Script(BaseModel):
    full_text: str = ""
    lines: list[ScriptLine] = Field(default_factory=list)
    language: str = ""
