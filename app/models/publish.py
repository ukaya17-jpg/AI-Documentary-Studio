from pydantic import BaseModel, Field


class PublishResult(BaseModel):
    success: bool = False
    request_id: str = ""
    error: str = ""
    platforms: list[str] = Field(default_factory=list)
    # ISO 8601 UTC timestamp of the publish attempt.
    published_at: str = ""
