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
    # Only meaningful for the ai_generated provider -- the Kling "duration"
    # tier ("5" or "10" seconds) to request for THIS scene's clip. Named
    # distinctly from the existing (currently unused) `duration: float`
    # field below to avoid type/semantic confusion: this is a fal.ai request
    # parameter (a string enum), not a measured clip length.
    ai_duration: str = "5"
    url: str = ""
    local_path: str = ""
    duration: float = 0.0


class AssetPlan(BaseModel):
    candidates: list[AssetCandidate] = Field(default_factory=list)
    downloaded_paths: list[str] = Field(default_factory=list)
