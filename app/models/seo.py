from pydantic import BaseModel, Field


class SeoMetadata(BaseModel):
    title: str = ""
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
