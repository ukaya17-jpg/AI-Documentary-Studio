from pydantic import BaseModel, Field


class OutlineSection(BaseModel):
    title: str
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)


class Outline(BaseModel):
    title: str
    hook: str = ""
    sections: list[OutlineSection] = Field(default_factory=list)
    closing: str = ""
