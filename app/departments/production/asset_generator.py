"""Asset stage: turn storyboard shots into a flat, scene-ordered asset plan.

No downloading/generation happens here -- this only decides *what* each
scene needs (a stock-search keyword, or a generative-model prompt).
app.departments.production.asset_downloader / ai_video_generator perform
the actual download/generation.
"""

from app.config.profile_dimensions import TopicCategory
from app.models.asset import AssetCandidate, AssetPlan
from app.models.character import CharacterReference
from app.models.script import Script
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

# Must match app.departments.creative.script_generator._WORDS_PER_SECOND --
# duplicated locally (not imported) since it's that module's private target
# rate, same pattern already used elsewhere in this codebase for a fallback
# constant that can't be cleanly imported (see webui/Main.py's
# DEFAULT_SUBTITLE_SETTINGS history).
_WORDS_PER_SECOND = 2.3


def _kling_duration_for_word_count(word_count: int) -> str:
    """Real per-scene word count (from the ALREADY-GENERATED script, not a
    pre-generation Pacing target) -> the Kling duration tier ("5" or "10",
    the only two values Kling accepts) needed to cover it without looping.

    Rounds UP (never down) for the same reason
    _ASSET_DOWNLOAD_DURATION_SAFETY_MULTIPLIER over-fetches on the stock
    path: under-provisioning causes combine_videos() to loop/repeat clips
    to fill the gap (the "repeated frame" defect this function exists to
    avoid) -- but unlike the stock path, generating extra AI clips costs
    real money, so this only bumps the SPECIFIC scenes that actually need
    it to "10", instead of a blanket policy applied to every scene.
    """
    estimated_seconds = word_count / _WORDS_PER_SECOND
    return "5" if estimated_seconds <= 5.0 else "10"


def build_asset_plan(
    storyboard: Storyboard,
    provider: str = "pexels",
    topic_category: TopicCategory | None = None,
    script: Script | None = None,
    character_reference: CharacterReference | None = None,
) -> AssetPlan:
    narration_by_scene = {line.scene_index: line.text for line in script.lines} if script else {}

    candidates = []
    for shot in storyboard.shots:
        if provider == "ai_generated":
            prompt = f"{shot.shot_type}: {shot.description}" if shot.shot_type else shot.description
            if topic_category == TopicCategory.film_highlights:
                prompt += _FILM_HIGHLIGHTS_LIKENESS_GUARD
            if character_reference is not None:
                # Kling O1 Reference-to-Video only applies `elements[]` when
                # the prompt explicitly addresses it as "@Element1" (see
                # docs/character-consistency-research.md) -- without this
                # prefix the reference images are silently ignored.
                prompt = f"Take @Element1 as {character_reference.name}. {prompt}"
            # script=None (no real narration text available yet, e.g. an
            # isolated/unit-test call) preserves the old, always-"5"
            # behavior exactly -- no regression.
            narration_text = narration_by_scene.get(shot.scene_index, "")
            ai_duration = (
                _kling_duration_for_word_count(len(narration_text.split()))
                if narration_text
                else "5"
            )
            candidates.append(
                AssetCandidate(
                    scene_index=shot.scene_index,
                    provider=provider,
                    prompt=prompt,
                    ai_duration=ai_duration,
                )
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
