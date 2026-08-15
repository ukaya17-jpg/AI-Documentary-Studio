"""AssetDownload-equivalent stage for AI-generated video clips (fal.ai/Kling).

Parallel counterpart to app.departments.production.asset_downloader -- same
AssetPlan-in/AssetPlan-out shape, but instead of searching/downloading stock
footage, it submits one text-to-video generation job per scene to fal.ai,
polls all pending jobs together (a single-threaded round-robin loop, not
real concurrency -- fal.ai's own queue already handles the account's actual
concurrency limit, submitted jobs just wait their turn server-side), and
downloads each finished clip.

Deliberately a separate module, not a branch inside asset_downloader.py:
the two paths have fundamentally different operational profiles (stock:
synchronous, seconds, free, cheap-retry; AI: async, minutes, real $ cost,
content-policy-rejection risk) -- see PROGRESS.md for the planning
rationale.

Never falls back to stock footage automatically on failure. A failed clip
raises AIVideoGenerationError with structured per-scene detail instead of
silently substituting something else -- matching this project's "no silent
fallback for a paid action" principle (same spirit as publisher.py's
manual-confirmation-only publishing).
"""

import os
import time
from typing import Callable

from loguru import logger

from app.models.asset import AssetPlan
from app.models.character import CharacterReference
from app.services.fal_video import fal_video_service
from app.utils import utils

_POLL_INTERVAL_SECONDS = 10.0
# ~15min safety ceiling per clip -- fal.ai's own model page quotes ~6min for
# a single standard-tier Kling clip, this leaves headroom before giving up.
_JOB_TIMEOUT_SECONDS = 900.0
_MAX_POLL_ITERATIONS = int(_JOB_TIMEOUT_SECONDS // _POLL_INTERVAL_SECONDS)
_TERMINAL_STATUS = "COMPLETED"
_FAILED_STATUSES = {"ERROR", "FAILED"}


class AIVideoGenerationError(Exception):
    """Raised when one or more scene clips could not be generated.

    `failures` is a list of (scene_index, error_message) tuples so the
    caller (webui) can show exactly which scene failed and why.
    `completed_paths` (scene_index -> local file path) carries any clips
    that WERE generated successfully -- real money was already spent on
    those, so a caller can keep them and only needs a fallback for the
    scenes actually listed in `failures`, instead of discarding everything.
    """

    def __init__(
        self,
        failures: list[tuple[int, str]],
        completed_paths: dict[int, str] | None = None,
    ):
        self.failures = failures
        self.completed_paths = completed_paths or {}
        super().__init__(
            f"AI video generation failed for {len(failures)} scene(s): {failures}"
        )


def generate_ai_clips(
    asset_plan: AssetPlan,
    task_id: str,
    aspect_ratio: str = "9:16",
    character_references_by_scene: dict[int, list[CharacterReference]] | None = None,
    on_substage_progress: Callable[[int, int], None] | None = None,
) -> AssetPlan:
    """Generate one AI video clip per asset_plan candidate via fal.ai/Kling.

    Each candidate's OWN `ai_duration` ("5" or "10", set per-scene by
    asset_generator.build_asset_plan() from that scene's real narration word
    count) is used -- not a single duration shared by every clip. This way
    only the specific scenes whose real narration actually needs the extra
    seconds get billed for "10"; scenes that fit in "5" stay at "5" (see
    asset_generator._kling_duration_for_word_count for the cost rationale).

    `character_references_by_scene`, if given, maps each candidate's
    scene_index to ITS OWN reference list, passed to that candidate's
    submit_video_job() call as `character_elements` (one dict per
    character/location, in @ElementN order, matching asset_generator.
    build_asset_plan's per-scene prompt prefix EXACTLY -- same dict, same
    order, built once in default_pipeline.py and passed to both functions)
    -- see docs/character-consistency-research.md and fal_video.
    submit_video_job's docstring for why this always routes to Kling O1
    regardless of the globally configured AI video provider. "Sahne Bazlı
    Otomatik Kadrolama" planı (kullanıcı onaylı): this is per-scene (not a
    single global list applied to every clip) specifically so Auto-mode
    casting can vary which character/location appears clip-to-clip;
    fixed/manual selection still works identically, just via the SAME dict
    with every scene_index mapped to the same list (see default_pipeline.py).

    Submits every candidate's job up front, then polls all still-pending
    jobs together each iteration until each one completes, fails, or the
    shared timeout is reached. Downloads each finished clip into task_id's
    storage directory. On full success, populates `asset_plan.downloaded_paths`
    in the same scene order as `asset_plan.candidates`, exactly like the
    stock-footage path, so downstream (timeline_builder) sees an ordinary
    AssetPlan either way.

    `on_substage_progress(completed, total)`, if given, is called after each
    clip finishes downloading -- purely additive, for a caller (webui) to
    drive a live "N/M clips done" indicator during what can be many minutes
    of waiting.

    Raises AIVideoGenerationError if ANY clip fails or times out -- clips
    that DID succeed are still downloaded and returned via the exception's
    `completed_paths` (see its docstring), since that money was already
    spent regardless of the other failures.
    """
    candidates = [c for c in asset_plan.candidates if c.prompt]
    if not candidates:
        return asset_plan

    total = len(candidates)
    task_directory = utils.task_dir(task_id)

    # app_id is carried alongside request_id (not re-derived from the live
    # provider config at poll time) so a character job stays correctly
    # addressed even if the global fal_ai_video_model setting changes while
    # it's in flight -- see fal_video.submit_video_job's returned "app_id".
    jobs: dict[int, tuple[str, str]] = {}
    failures: list[tuple[int, str]] = []
    for candidate in candidates:
        scene_references = (character_references_by_scene or {}).get(candidate.scene_index) or []
        character_elements = (
            [ref.model_dump() for ref in scene_references] if scene_references else None
        )
        result = fal_video_service.submit_video_job(
            candidate.prompt,
            duration=candidate.ai_duration,
            aspect_ratio=aspect_ratio,
            character_elements=character_elements,
        )
        if result["success"]:
            jobs[candidate.scene_index] = (result["request_id"], result.get("app_id", ""))
        else:
            failures.append((candidate.scene_index, result["error"]))
            logger.warning(
                f"ai_video_generator: submit failed for scene {candidate.scene_index}: {result['error']}"
            )

    completed_paths: dict[int, str] = {}
    pending = dict(jobs)
    for _ in range(_MAX_POLL_ITERATIONS):
        if not pending:
            break
        for scene_index, (request_id, app_id) in list(pending.items()):
            status_result = fal_video_service.poll_job_status(request_id, app_id=app_id)
            if not status_result["success"]:
                failures.append((scene_index, status_result["error"]))
                del pending[scene_index]
                continue

            status = status_result["status"]
            if status in _FAILED_STATUSES:
                failures.append((scene_index, f"fal.ai job failed: {status}"))
                del pending[scene_index]
                continue
            if status != _TERMINAL_STATUS:
                continue  # IN_QUEUE / IN_PROGRESS -- check again next iteration

            result = fal_video_service.get_job_result(request_id, app_id=app_id)
            if not result["success"]:
                failures.append((scene_index, result["error"]))
                del pending[scene_index]
                continue

            dest_path = os.path.join(task_directory, f"ai_clip_scene_{scene_index}.mp4")
            if not fal_video_service.download_video(result["video_url"], dest_path):
                failures.append((scene_index, "failed to download generated clip"))
                del pending[scene_index]
                continue

            completed_paths[scene_index] = dest_path
            del pending[scene_index]
            if on_substage_progress is not None:
                on_substage_progress(len(completed_paths), total)

        if pending:
            time.sleep(_POLL_INTERVAL_SECONDS)

    for scene_index in pending:
        failures.append((scene_index, "timed out waiting for fal.ai job"))

    if failures:
        raise AIVideoGenerationError(failures, completed_paths=completed_paths)

    asset_plan.downloaded_paths = [completed_paths[c.scene_index] for c in candidates]
    return asset_plan
