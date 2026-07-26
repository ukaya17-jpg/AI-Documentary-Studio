"""Asset stage: turn storyboard shots into a flat, scene-ordered asset plan.

No downloading/generation happens here -- this only decides *what* each
scene needs (a stock-search keyword, or a generative-model prompt).
app.departments.production.asset_downloader / ai_video_generator perform
the actual download/generation.
"""

from app.config.profile_dimensions import TopicCategory
from app.models.asset import AssetCandidate, AssetPlan
from app.models.storyboard import Storyboard

# film_highlights prompts can reasonably reference real films/actors (that's
# the category's whole premise) -- for a generative model this carries a
# real risk the stock-search path doesn't have: reproducing a real person's
# likeness. This mirrors the existing copyright guard already applied to
# this category's narration (never quote real dialogue) -- same principle,
# extended to the AI-video prompt.
_FILM_HIGHLIGHTS_LIKENESS_GUARD = (
    " Avoid recreating the likeness of any real actor or public figure; use "
    "generic, representative imagery instead."
)


def build_asset_plan(
    storyboard: Storyboard,
    provider: str = "pexels",
    topic_category: TopicCategory | None = None,
) -> AssetPlan:
    candidates = []
    for shot in storyboard.shots:
        if provider == "ai_generated":
            prompt = f"{shot.shot_type}: {shot.description}" if shot.shot_type else shot.description
            if topic_category == TopicCategory.film_highlights:
                prompt += _FILM_HIGHLIGHTS_LIKENESS_GUARD
            candidates.append(
                AssetCandidate(scene_index=shot.scene_index, provider=provider, prompt=prompt)
            )
        else:
            candidates.append(
                AssetCandidate(
                    scene_index=shot.scene_index,
                    provider=provider,
                    search_term=shot.search_terms[0] if shot.search_terms else shot.description,
                )
            )
    return AssetPlan(candidates=candidates)
