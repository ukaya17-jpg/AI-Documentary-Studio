from pydantic import BaseModel, Field


class ResearchQuestion(BaseModel):
    question: str
    rationale: str = ""


class ResearchPlan(BaseModel):
    topic: str
    key_questions: list[ResearchQuestion] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    angles: list[str] = Field(default_factory=list)
    # Populated when app.services.web_search found a real grounding source for
    # this topic; empty otherwise (most topics -- see web_search's docstring).
    source_snippet: str = ""
    source_url: str = ""
