from pydantic import BaseModel


class IdeaCandidate(BaseModel):
    topic: str
    angle: str = ""
