from pydantic import BaseModel, Field


class ResearchQuestion(BaseModel):
    question: str
    rationale: str = ""


class ResearchPlan(BaseModel):
    topic: str
    key_questions: list[ResearchQuestion] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    angles: list[str] = Field(default_factory=list)
