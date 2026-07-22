"""SEO stage: title/description/hashtags, chapters, and engagement suggestions
for the finished documentary.

Reuses the existing app.services.llm.generate_social_metadata() (with its
own retry + heuristic-fallback behavior) for title/description/hashtags
instead of writing a new prompt.

chapters/end_screen_suggestion/pinned_comment are creator-facing advisory
metadata, not automated platform actions -- this pipeline's primary output
is short vertical video (YouTube Shorts/TikTok/Reels format), and YouTube
chapters + end screens are formally long-form-only features. Chapters are
still computed (deterministically, no LLM cost) since they become useful if
a longer-form video is ever produced from the same pipeline; a pinned
comment suggestion applies to Shorts too.
"""

from loguru import logger

from app.models.scene import ScenePlan
from app.models.script import Script
from app.models.seo import SeoMetadata
from app.services import llm
from app.services.documentary_llm_utils import generate_json


def generate_chapters(scene_plan: ScenePlan | None) -> list[str]:
    if not scene_plan or not scene_plan.scenes:
        return []
    chapters = []
    elapsed = 0.0
    for scene in scene_plan.scenes:
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        chapters.append(f"{minutes}:{seconds:02d} {scene.title}")
        elapsed += scene.duration_seconds
    return chapters


def build_engagement_prompt(topic: str, script: Script, language: str = "") -> str:
    prompt = (
        "You are a YouTube/social growth assistant. For the documentary below, "
        "suggest a short end-of-video note for the creator and a pinned comment "
        "to drive engagement."
        f'\n\nTopic: "{topic}"\n\nNarration:\n{script.full_text}'
    )
    if language and language != "auto":
        prompt += f"\n\nRespond in language: {language}"
    prompt += """

Respond with a single JSON object with exactly this shape:
{"end_screen_suggestion": "...", "pinned_comment": "..."}
end_screen_suggestion: one sentence telling the creator what to say/show in
the last few seconds (e.g., a subscribe prompt or a tease for a related
topic) -- advice for the creator, not on-screen text to render.
pinned_comment: a short, engaging comment (a question or a hook) the creator
can pin to drive replies. Do not include any other text."""
    return prompt


def generate_engagement_metadata(topic: str, script: Script, language: str = "auto") -> dict:
    try:
        data = generate_json(build_engagement_prompt(topic, script, language))
        return {
            "end_screen_suggestion": str(data.get("end_screen_suggestion", "")).strip(),
            "pinned_comment": str(data.get("pinned_comment", "")).strip(),
        }
    except Exception as e:
        logger.warning(f"seo_generator: engagement metadata generation failed: {e}")
        return {"end_screen_suggestion": "", "pinned_comment": ""}


def generate_seo_metadata(
    topic: str,
    script: Script,
    language: str = "auto",
    platform: str = "youtube_shorts",
    scene_plan: ScenePlan | None = None,
) -> SeoMetadata:
    result = llm.generate_social_metadata(
        video_subject=topic,
        video_script=script.full_text,
        language=language,
        platform=platform,
    )
    engagement = generate_engagement_metadata(topic, script, language)
    return SeoMetadata(
        title=result.get("title", ""),
        description=result.get("caption", ""),
        hashtags=list(result.get("hashtags", [])),
        chapters=generate_chapters(scene_plan),
        end_screen_suggestion=engagement["end_screen_suggestion"],
        pinned_comment=engagement["pinned_comment"],
    )
