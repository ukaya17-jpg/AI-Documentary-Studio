"""Generic fal.ai queue API client for AI-generated video clips (Kling models).

Provider-agnostic wrapper around fal.ai's queue-based REST API: submit a
text-to-video job, poll its status, fetch the result, download the clip.
No documentary-specific concepts here (scenes, storyboard, cost estimates,
...) -- see app.departments.production.ai_video_generator for that.

Docs: https://fal.ai/docs/model-endpoints/queue

Real money is spent per submitted job -- this module never retries a failed
submission automatically (unlike llm.py's generate_json) and never falls
back to anything; callers decide what to do with a {"success": False, ...}
result.
"""

import os

import requests
from loguru import logger

from app.config import config

_QUEUE_BASE = "https://queue.fal.run"
_SUBMIT_TIMEOUT = 30
_STATUS_TIMEOUT = 30
_RESULT_TIMEOUT = 30
_DOWNLOAD_TIMEOUT = 120

DEFAULT_KLING_MODEL = "fal-ai/kling-video/v1/standard/text-to-video"


class FalVideoService:
    def __init__(self):
        self.api_key = config.app.get("fal_api_key", "")
        self.model = config.app.get("fal_kling_model", DEFAULT_KLING_MODEL)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def _app_id(self) -> str:
        """The "owner/app-name" prefix of self.model, WITHOUT the version/
        tier subpath (e.g. "fal-ai/kling-video", not ".../v1/standard/
        text-to-video"). fal.ai's queue status/result/cancel endpoints must
        be called against this base app id -- the full endpoint (with
        subpath) is only valid for the initial POST submission. Confirmed
        empirically against the real API: including the subpath in a
        status/result GET returns 405 Method Not Allowed.
        """
        parts = self.model.split("/")
        return "/".join(parts[:2])

    def _headers(self) -> dict:
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

    def submit_video_job(
        self,
        prompt: str,
        duration: str = "5",
        aspect_ratio: str = "9:16",
        negative_prompt: str = "",
    ) -> dict:
        """Submit one text-to-video job. Never raises -- always returns
        {"success": True, "request_id": str} or {"success": False, "error": str}.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "fal.ai is not configured (missing fal_api_key)",
            }
        if not prompt.strip():
            return {"success": False, "error": "prompt is empty"}

        payload = {"prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio}
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        try:
            response = requests.post(
                f"{_QUEUE_BASE}/{self.model}",
                headers=self._headers(),
                json=payload,
                timeout=_SUBMIT_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            request_id = data.get("request_id", "")
            if not request_id:
                return {"success": False, "error": "fal.ai response missing request_id"}
            return {"success": True, "request_id": request_id}
        except Exception as e:
            logger.warning(f"fal_video: submit_video_job failed: {e}")
            return {"success": False, "error": str(e)}

    def poll_job_status(self, request_id: str) -> dict:
        """Returns {"success": True, "status": "IN_QUEUE"|"IN_PROGRESS"|"COMPLETED"}
        or {"success": False, "error": str}.
        """
        try:
            response = requests.get(
                f"{_QUEUE_BASE}/{self._app_id}/requests/{request_id}/status",
                headers=self._headers(),
                timeout=_STATUS_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "")
            if not status:
                return {"success": False, "error": "fal.ai status response missing status"}
            return {"success": True, "status": status}
        except Exception as e:
            logger.warning(f"fal_video: poll_job_status failed for {request_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_job_result(self, request_id: str) -> dict:
        """Returns {"success": True, "video_url": str} or {"success": False, "error": str}."""
        try:
            response = requests.get(
                f"{_QUEUE_BASE}/{self._app_id}/requests/{request_id}",
                headers=self._headers(),
                timeout=_RESULT_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            video_url = (data.get("video") or {}).get("url", "")
            if not video_url:
                return {"success": False, "error": "fal.ai result missing video url"}
            return {"success": True, "video_url": video_url}
        except Exception as e:
            logger.warning(f"fal_video: get_job_result failed for {request_id}: {e}")
            return {"success": False, "error": str(e)}

    def download_video(self, video_url: str, dest_path: str) -> bool:
        """Downloads the generated clip to dest_path. Returns True/False, never raises."""
        try:
            response = requests.get(video_url, timeout=_DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(response.content)
            return True
        except Exception as e:
            logger.warning(f"fal_video: download_video failed for {video_url}: {e}")
            return False


# Singleton instance
fal_video_service = FalVideoService()
