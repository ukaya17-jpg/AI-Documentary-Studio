from pydantic import BaseModel, Field


class AssetCandidate(BaseModel):
    scene_index: int
    provider: str = "pexels"
    search_term: str = ""
    url: str = ""
    local_path: str = ""
    duration: float = 0.0


class AssetPlan(BaseModel):
    candidates: list[AssetCandidate] = Field(default_factory=list)
    downloaded_paths: list[str] = Field(default_factory=list)
