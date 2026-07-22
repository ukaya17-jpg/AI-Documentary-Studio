from pydantic import BaseModel, Field

QUALITY_PASS_THRESHOLD = 3.0


class QualityVerdict(BaseModel):
    coherence_score: int = Field(ge=1, le=5)
    pacing_fit_score: int = Field(ge=1, le=5)
    seo_quality_score: int = Field(ge=1, le=5)
    overall_score: float
    passed: bool
    issues: list[str] = Field(default_factory=list)
