from pydantic import BaseModel, Field


class AssetCandidate(BaseModel):
    scene_index: int
    provider: str = "pexels"
    search_term: str = ""
    # Only populated for the ai_generated provider -- a descriptive prompt
    # (from the storyboard shot's description) for a generative video model,
    # as opposed to search_term's short keyword phrase for a stock-footage
    # search index. The two are not interchangeable inputs.
    prompt: str = ""
    url: str = ""
    local_path: str = ""
    duration: float = 0.0


class AssetPlan(BaseModel):
    candidates: list[AssetCandidate] = Field(default_factory=list)
    downloaded_paths: list[str] = Field(default_factory=list)
