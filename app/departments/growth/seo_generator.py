"""SEO stage: title/description/hashtags for the finished documentary.

Reuses the existing app.services.llm.generate_social_metadata() (with its
own retry + heuristic-fallback behavior) instead of writing a new prompt.
"""

from app.models.script import Script
from app.models.seo import SeoMetadata
from app.services import llm


def generate_seo_metadata(
    topic: str,
    script: Script,
    language: str = "auto",
    platform: str = "youtube_shorts",
) -> SeoMetadata:
    result = llm.generate_social_metadata(
        video_subject=topic,
        video_script=script.full_text,
        language=language,
        platform=platform,
    )
    return SeoMetadata(
        title=result.get("title", ""),
        description=result.get("caption", ""),
        hashtags=list(result.get("hashtags", [])),
    )
