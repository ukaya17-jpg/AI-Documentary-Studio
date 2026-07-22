"""Asset stage: turn storyboard shots into a flat, scene-ordered asset search plan.

No downloading happens here -- this only decides *what* to search for per
scene. app.services.asset_downloader performs the actual download.
"""

from app.models.asset import AssetCandidate, AssetPlan
from app.models.storyboard import Storyboard


def build_asset_plan(storyboard: Storyboard, provider: str = "pexels") -> AssetPlan:
    candidates = [
        AssetCandidate(
            scene_index=shot.scene_index,
            provider=provider,
            search_term=shot.search_terms[0] if shot.search_terms else shot.description,
        )
        for shot in storyboard.shots
    ]
    return AssetPlan(candidates=candidates)
