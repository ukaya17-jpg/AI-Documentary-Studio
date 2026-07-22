from pydantic import BaseModel, Field


class SeoMetadata(BaseModel):
    title: str = ""
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
    # Creator-facing advisory metadata, not automated platform actions.
    # "MM:SS Title" markers -- only meaningful for a long-form upload, since
    # YouTube Shorts (this pipeline's primary output) don't support chapters.
    chapters: list[str] = Field(default_factory=list)
    end_screen_suggestion: str = ""
    pinned_comment: str = ""
