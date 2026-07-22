from pydantic import BaseModel


class WebSearchResult(BaseModel):
    heading: str = ""
    abstract: str
    source_url: str = ""
