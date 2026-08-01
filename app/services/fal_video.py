"""Generic fal.ai queue API client for AI-generated video clips (Kling/Hailuo).

Provider-agnostic wrapper around fal.ai's queue-based REST API: submit a
text-to-video job, poll its status, fetch the result, download the clip.
No documentary-specific concepts here (scenes, storyboard, cost estimates,
...) -- see app.departments.production.ai_video_generator for that.

Docs: https://fal.ai/docs/model-endpoints/queue

Real money is spent per submitted job -- this module never retries a failed
submission automatically (unlike llm.py's generate_json) and never falls
back to anything; callers decide what to do with a {"success": False, ...}
result.

ADIM 3 (Provider Sistemi keşif raporu, kullanıcı onaylı): fal_ai_video_model
config'i ile Kling/Hailuo arasında seçim -- yeni bir Protocol/ABC katmanı
YOK (kullanıcı bilinçli olarak istemedi), voice.tts()'in kendi kanıtlanmış
deseniyle (basit if/elif + model-özel payload fonksiyonu) tutarlı, küçük
bir dispatch. submit_video_job()'un PUBLIC arayüzü hiç değişmedi --
ai_video_generator.py'nin tek satırı bile dokunulmadı.
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
DEFAULT_HAILUO_MODEL = "fal-ai/minimax/hailuo-02/standard/text-to-video"
# GÖREV 3 (gece oturumu, TAM OTONOMİ): "veo3.1/fast" -- Veo 2 ($0.50/s,
# fal.ai fiyatlandırmasına göre) ve Veo 3.1 standard ($0.20-0.40/s) yerine
# kasıtlı olarak Veo'nun EN UCUZ kademesi (720p, sessiz: $0.10/s) seçildi.
# Yine de Kling'in (~$0.045/s) ~2x'i -- bkz. PROGRESS.md maliyet notu.
DEFAULT_VEO_MODEL = "fal-ai/veo3.1/fast"
# "Bao" planı (kullanıcı onaylı): karakter-tutarlı üretim, gerçek API ile
# doğrulandı (docs/character-consistency-research.md) -- ne Hailuo ne Veo bu
# özelliği destekliyor, o yüzden bu, `fal_ai_video_model` (kling/hailuo/veo)
# seçiminden AYRI, kendi sabit modeli. Aynı "fal-ai/kling-video" app_id'sini
# DEFAULT_KLING_MODEL ile paylaşıyor (ikisi de Kling'in aynı fal.ai
# namespace'inde), bu yüzden status/result endpoint'leri her iki model için
# de aynı şekilde çalışır.
DEFAULT_KLING_CHARACTER_MODEL = "fal-ai/kling-video/o1/standard/reference-to-video"
_DEFAULT_VIDEO_PROVIDER = "kling"

# Kling ("5"/"10") ve Hailuo ("6"/"10", resmi API dokümantasyonuna göre)
# farklı duration enum'ları kabul ediyor -- asset_generator.py'nin
# _kling_duration_for_word_count()'u (AssetCandidate.ai_duration'ın tek
# kaynağı) BİLİNÇLİ OLARAK Kling-şekilli kalıyor (webui'nin maliyet
# tahmini de bu iki değere dayanıyor) -- burada, SADECE Hailuo API'sine
# giden payload'da, en yakın geçerli Hailuo değerine eşleniyor.
_HAILUO_DURATION_MAP = {"5": "6", "10": "10"}

# Veo yalnızca "4s"/"6s"/"8s" kabul ediyor (fal.ai dokümantasyonuna göre) --
# Kling'in "5"i tam ortada, kısa kalmaması için YUKARI (6s) yuvarlanıyor;
# "10" Veo'nun desteklediği maksimumun (8s) üzerinde olduğu için aşağı
# kırpılıyor (daha yüksek bir seçenek yok).
_VEO_DURATION_MAP = {"5": "6s", "10": "8s"}


class FalVideoService:
    """`api_key`/`provider`/`model` are properties (not __init__-assigned
    attributes) so config.toml changes take effect immediately for the
    module-level `fal_video_service` singleton below -- it's imported once
    per process (Streamlit reruns the script but not the module cache), so
    freezing these at construction time would require a full service
    restart for a provider switch to ever take effect. Needed for GÖREV 3's
    webui provider selector (Kling/Veo) to actually work within one running
    session, not just after a restart.
    """

    @property
    def api_key(self) -> str:
        return config.app.get("fal_api_key", "")

    @property
    def provider(self) -> str:
        return config.app.get("fal_ai_video_model", _DEFAULT_VIDEO_PROVIDER)

    @property
    def model(self) -> str:
        if self.provider == "hailuo":
            return config.app.get("fal_hailuo_model", DEFAULT_HAILUO_MODEL)
        if self.provider == "veo":
            return config.app.get("fal_veo_model", DEFAULT_VEO_MODEL)
        return config.app.get("fal_kling_model", DEFAULT_KLING_MODEL)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def character_model(self) -> str:
        return config.app.get("fal_kling_character_model", DEFAULT_KLING_CHARACTER_MODEL)

    @staticmethod
    def _app_id_for(model: str) -> str:
        """The "owner/app-name" prefix of a model id, WITHOUT the version/
        tier subpath (e.g. "fal-ai/kling-video", not ".../v1/standard/
        text-to-video"). fal.ai's queue status/result/cancel endpoints must
        be called against this base app id -- the full endpoint (with
        subpath) is only valid for the initial POST submission. Confirmed
        empirically against the real API: including the subpath in a
        status/result GET returns 405 Method Not Allowed.
        """
        parts = model.split("/")
        return "/".join(parts[:2])

    @property
    def _app_id(self) -> str:
        return self._app_id_for(self.model)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_kling_payload(
        self, prompt: str, duration: str, aspect_ratio: str, negative_prompt: str
    ) -> dict:
        payload = {"prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio}
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        return payload

    def _build_hailuo_payload(self, prompt: str, duration: str) -> dict:
        """Hailuo'nun (fal-ai/minimax/hailuo-02, "standard" tier) alanları
        Kling'den farklı: "aspect_ratio" YOK, duration "6"/"10" (Kling'in
        "5"/"10"una değil).

        GERÇEK API İLE DOĞRULANDI (varsayım değil, bkz. PROGRESS.md ADIM 3):
        bu endpoint 9:16 (dikey) DESTEKLEMİYOR -- prompt metninde açıkça
        "vertical portrait shot, 9:16 aspect ratio" istense bile, çıktı
        HER ZAMAN sabit 1366x768 (yatay, ~16:9) geliyor. Bu yüzden
        Documentary Studio'nun varsayılan (ve en yaygın) 9:16 modu için
        Hailuo UYGUN DEĞİL -- sadece 16:9 (landscape) modda, ve düşük
        çözünürlük (1366x768, HD'nin altında) bilinerek kabul edilirse
        kullanılabilir. Bu bulgu nedeniyle kullanıcının kendi v1/v2 ayrımı
        (v2 = webui'de per-generation model seçici) BİLİNÇLİ OLARAK
        uygulanmadı -- sadece config-seviyesi anahtar var, hiçbir webui
        elemanı Hailuo'yu tanıtmıyor/önermiyor.
        """
        return {
            "prompt": prompt,
            "duration": _HAILUO_DURATION_MAP.get(duration, duration),
        }

    def _build_veo_payload(
        self, prompt: str, duration: str, aspect_ratio: str, negative_prompt: str
    ) -> dict:
        """Veo 3.1 (fal-ai/veo3.1, "fast" tier) -- GERÇEK API İLE DOĞRULANDI
        (bkz. PROGRESS.md GÖREV 3): 9:16 (dikey) DESTEKLENİYOR, Hailuo'nun
        aksine. `generate_audio` kasıtlı olarak False -- Veo'nun kendi ses
        üretimi hem ekstra maliyet (~1.5x) hem de bu projenin KENDİ narrasyon/
        altyazı sesiyle çakışan, gereksiz bir ikinci ses katmanı demek.
        """
        payload = {
            "prompt": prompt,
            "duration": _VEO_DURATION_MAP.get(duration, "8s"),
            "aspect_ratio": aspect_ratio,
            "resolution": "720p",
            "generate_audio": False,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        return payload

    def _build_kling_character_payload(
        self, prompt: str, duration: str, aspect_ratio: str, character_elements: list[dict]
    ) -> dict:
        """fal-ai/kling-video/o1/standard/reference-to-video's real `elements[]`
        request shape (`OmniVideoElementInput`) -- see
        docs/character-consistency-research.md for the live schema source and
        a real, verified test. Duration here is O1's own "3".."10" enum;
        AssetCandidate.ai_duration only ever produces "5"/"10", both valid in
        this range too, so unlike Hailuo/Veo no remapping is needed.
        """
        return {
            "prompt": prompt,
            "elements": character_elements,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }

    def submit_video_job(
        self,
        prompt: str,
        duration: str = "5",
        aspect_ratio: str = "9:16",
        negative_prompt: str = "",
        character_elements: list[dict] | None = None,
    ) -> dict:
        """Submit one text-to-video job. Never raises -- always returns
        {"success": True, "request_id": str, "app_id": str} or
        {"success": False, "error": str}.

        `duration` is always given in Kling's "5"/"10" shape regardless of
        the active provider (matches AssetCandidate.ai_duration, the single
        source of truth webui's cost estimate also reads) -- if the active
        provider is Hailuo, it's internally remapped to Hailuo's own
        duration enum before being sent.

        `character_elements`, if given (see CharacterReference.model_dump()),
        ALWAYS routes to Kling O1 Reference-to-Video regardless of the
        globally configured `fal_ai_video_model` provider (kling/hailuo/veo)
        -- only Kling O1 supports character-reference consistency (see
        docs/character-consistency-research.md), so the provider selector is
        deliberately bypassed here rather than silently generating a
        character-inconsistent clip on Hailuo/Veo.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "fal.ai is not configured (missing fal_api_key)",
            }
        if not prompt.strip():
            return {"success": False, "error": "prompt is empty"}

        if character_elements:
            model = self.character_model
            payload = self._build_kling_character_payload(
                prompt, duration, aspect_ratio, character_elements
            )
        elif self.provider == "hailuo":
            model = self.model
            payload = self._build_hailuo_payload(prompt, duration)
        elif self.provider == "veo":
            model = self.model
            payload = self._build_veo_payload(prompt, duration, aspect_ratio, negative_prompt)
        else:
            model = self.model
            payload = self._build_kling_payload(prompt, duration, aspect_ratio, negative_prompt)

        try:
            response = requests.post(
                f"{_QUEUE_BASE}/{model}",
                headers=self._headers(),
                json=payload,
                timeout=_SUBMIT_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            request_id = data.get("request_id", "")
            if not request_id:
                return {"success": False, "error": "fal.ai response missing request_id"}
            return {
                "success": True,
                "request_id": request_id,
                "app_id": self._app_id_for(model),
            }
        except Exception as e:
            logger.warning(f"fal_video: submit_video_job failed: {e}")
            return {"success": False, "error": str(e)}

    def poll_job_status(self, request_id: str, app_id: str | None = None) -> dict:
        """Returns {"success": True, "status": "IN_QUEUE"|"IN_PROGRESS"|"COMPLETED"}
        or {"success": False, "error": str}.

        `app_id`, if given, overrides the app id derived from the currently
        configured provider (self._app_id) -- needed so a job submitted for
        one model (e.g. a character job, always Kling regardless of the
        active provider) is still polled against the SAME app id even if the
        global provider setting changes in between (see submit_video_job's
        returned "app_id").
        """
        try:
            response = requests.get(
                f"{_QUEUE_BASE}/{app_id or self._app_id}/requests/{request_id}/status",
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

    def get_job_result(self, request_id: str, app_id: str | None = None) -> dict:
        """Returns {"success": True, "video_url": str} or {"success": False, "error": str}.

        See poll_job_status's `app_id` docstring -- same override reason.
        """
        try:
            response = requests.get(
                f"{_QUEUE_BASE}/{app_id or self._app_id}/requests/{request_id}",
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
