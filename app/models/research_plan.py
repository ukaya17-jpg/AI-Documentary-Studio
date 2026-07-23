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
    # Explicit transparency flag (GÖREV 8b, gece oturumu): equivalent to
    # bool(source_url), but named for what it means so callers (webui) don't
    # have to know that empty-string-as-sentinel is the convention. True only
    # when a real DuckDuckGo/Wikipedia source was found and injected into the
    # LLM prompt -- False means this research brief is the LLM's own
    # knowledge, unverified against any external source.
    grounded: bool = False
