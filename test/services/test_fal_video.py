import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.fal_video import FalVideoService

_CONFIGURED = {
    "fal_api_key": "test-fal-key",
    "fal_kling_model": "fal-ai/kling-video/v1/standard/text-to-video",
}
_UNCONFIGURED = {"fal_api_key": "", "fal_kling_model": ""}


def _response(json_data, status_ok=True):
    r = MagicMock()
    r.json.return_value = json_data
    if not status_ok:
        r.raise_for_status.side_effect = Exception("HTTP error")
    else:
        r.raise_for_status = MagicMock()
    return r


class TestIsConfigured(unittest.TestCase):
    @patch("app.services.fal_video.config.app", _CONFIGURED)
    def test_true_when_api_key_present(self):
        self.assertTrue(FalVideoService().is_configured())

    @patch("app.services.fal_video.config.app", _UNCONFIGURED)
    def test_false_when_api_key_missing(self):
        self.assertFalse(FalVideoService().is_configured())

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    def test_app_id_strips_version_tier_subpath(self):
        # fal.ai'nin queue API'sinde status/result endpoint'leri sadece
        # "owner/app-name" kabul ediyor -- submit URL'indeki tam alt-yolu
        # (version/tier/endpoint-variant) DEĞİL. Gerçek API doğrulamasında
        # bulundu: subpath dahil edilirse 405 Method Not Allowed.
        self.assertEqual(FalVideoService()._app_id, "fal-ai/kling-video")

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    def test_uses_configured_model_and_default_fallback(self):
        self.assertEqual(
            FalVideoService().model, "fal-ai/kling-video/v1/standard/text-to-video"
        )
        with patch("app.services.fal_video.config.app", {"fal_api_key": "k"}):
            # fal_kling_model not set at all -- must fall back to the module default.
            from app.services.fal_video import DEFAULT_KLING_MODEL

            self.assertEqual(FalVideoService().model, DEFAULT_KLING_MODEL)


_HAILUO_CONFIGURED = {
    "fal_api_key": "test-fal-key",
    "fal_ai_video_model": "hailuo",
}


class TestHailuoProviderSelection(unittest.TestCase):
    """ADIM 3 (kullanıcı onaylı): fal_ai_video_model config'i ile Kling/
    Hailuo arasında seçim -- yeni bir Protocol/ABC katmanı yok, voice.tts()
    ile aynı basit if/elif deseni.
    """

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    def test_defaults_to_kling_when_fal_ai_video_model_not_set(self):
        service = FalVideoService()
        self.assertEqual(service.provider, "kling")
        self.assertEqual(
            service.model, "fal-ai/kling-video/v1/standard/text-to-video"
        )

    @patch("app.services.fal_video.config.app", _HAILUO_CONFIGURED)
    def test_uses_hailuo_model_when_selected(self):
        from app.services.fal_video import DEFAULT_HAILUO_MODEL

        service = FalVideoService()
        self.assertEqual(service.provider, "hailuo")
        self.assertEqual(service.model, DEFAULT_HAILUO_MODEL)

    @patch(
        "app.services.fal_video.config.app",
        {**_HAILUO_CONFIGURED, "fal_hailuo_model": "fal-ai/minimax/hailuo-2.3/standard/text-to-video"},
    )
    def test_uses_configured_hailuo_model_override(self):
        service = FalVideoService()
        self.assertEqual(
            service.model, "fal-ai/minimax/hailuo-2.3/standard/text-to-video"
        )

    @patch("app.services.fal_video.config.app", _HAILUO_CONFIGURED)
    def test_app_id_strips_subpath_for_hailuo_too(self):
        # Aynı queue API kısıtı Hailuo için de geçerli (submit URL'i tam
        # alt-yolu kullanır, status/result sadece "owner/app-name").
        self.assertEqual(FalVideoService()._app_id, "fal-ai/minimax")


class TestSubmitVideoJob(unittest.TestCase):
    @patch("app.services.fal_video.config.app", _UNCONFIGURED)
    @patch("app.services.fal_video.requests.post")
    def test_unconfigured_skips_request(self, mock_post):
        result = FalVideoService().submit_video_job("a wide shot of ancient ruins")

        self.assertFalse(result["success"])
        self.assertIn("not configured", result["error"])
        mock_post.assert_not_called()

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.post")
    def test_empty_prompt_skips_request(self, mock_post):
        result = FalVideoService().submit_video_job("   ")

        self.assertFalse(result["success"])
        self.assertIn("empty", result["error"])
        mock_post.assert_not_called()

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.post")
    def test_success_returns_request_id_and_sends_expected_payload(self, mock_post):
        mock_post.return_value = _response({"request_id": "req-123"})

        result = FalVideoService().submit_video_job(
            "a wide shot of ancient ruins", duration="10", aspect_ratio="9:16"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["request_id"], "req-123")
        call = mock_post.call_args
        self.assertEqual(
            call.args[0],
            "https://queue.fal.run/fal-ai/kling-video/v1/standard/text-to-video",
        )
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Key test-fal-key")
        self.assertEqual(call.kwargs["json"]["prompt"], "a wide shot of ancient ruins")
        self.assertEqual(call.kwargs["json"]["duration"], "10")
        self.assertEqual(call.kwargs["json"]["aspect_ratio"], "9:16")

    @patch("app.services.fal_video.config.app", _HAILUO_CONFIGURED)
    @patch("app.services.fal_video.requests.post")
    def test_hailuo_payload_has_no_aspect_ratio_and_remaps_duration(self, mock_post):
        """Hailuo'nun (resmi dokümana göre) aspect_ratio parametresi yok,
        duration enum'ı Kling'den farklı ("6"/"10", "5"/"10" değil).
        AssetCandidate.ai_duration hâlâ Kling-şekilli "5"/"10" üretiyor
        (webui'nin maliyet tahmini de buna dayanıyor) -- burada SADECE
        Hailuo'ya giden payload'da en yakın geçerli değere eşleniyor.
        """
        mock_post.return_value = _response({"request_id": "req-456"})

        result = FalVideoService().submit_video_job(
            "a wide shot of ancient ruins", duration="5", aspect_ratio="9:16"
        )

        self.assertTrue(result["success"])
        call = mock_post.call_args
        self.assertEqual(
            call.args[0],
            "https://queue.fal.run/fal-ai/minimax/hailuo-02/standard/text-to-video",
        )
        sent_payload = call.kwargs["json"]
        self.assertEqual(sent_payload["duration"], "6")
        self.assertNotIn("aspect_ratio", sent_payload)

    @patch("app.services.fal_video.config.app", _HAILUO_CONFIGURED)
    @patch("app.services.fal_video.requests.post")
    def test_hailuo_duration_ten_stays_ten(self, mock_post):
        mock_post.return_value = _response({"request_id": "req-789"})

        FalVideoService().submit_video_job("a wide shot", duration="10")

        self.assertEqual(mock_post.call_args.kwargs["json"]["duration"], "10")

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.post")
    def test_missing_request_id_in_response_is_an_error(self, mock_post):
        mock_post.return_value = _response({})

        result = FalVideoService().submit_video_job("a wide shot of ancient ruins")

        self.assertFalse(result["success"])
        self.assertIn("request_id", result["error"])

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.post")
    def test_network_error_never_raises(self, mock_post):
        mock_post.side_effect = ConnectionError("network unreachable")

        result = FalVideoService().submit_video_job("a wide shot of ancient ruins")

        self.assertFalse(result["success"])
        self.assertIn("network unreachable", result["error"])


class TestPollJobStatus(unittest.TestCase):
    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.get")
    def test_returns_status_on_success(self, mock_get):
        mock_get.return_value = _response({"status": "IN_PROGRESS"})

        result = FalVideoService().poll_job_status("req-123")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "IN_PROGRESS")
        # Gerçek fal.ai API'sinde doğrulandı: status/result URL'leri sadece
        # "owner/app-name" kullanmalı (ör. "fal-ai/kling-video"), submit
        # URL'indeki tam alt-yol (v1/standard/text-to-video) DAHİL EDİLMEMELİ
        # -- dahil edilirse 405 Method Not Allowed dönüyor (gerçek API
        # doğrulamasında bulunan bir bug, düzeltildi).
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://queue.fal.run/fal-ai/kling-video/requests/req-123/status",
        )

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.get")
    def test_missing_status_field_is_an_error(self, mock_get):
        mock_get.return_value = _response({})

        result = FalVideoService().poll_job_status("req-123")

        self.assertFalse(result["success"])

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.get")
    def test_network_error_never_raises(self, mock_get):
        mock_get.side_effect = ConnectionError("timeout")

        result = FalVideoService().poll_job_status("req-123")

        self.assertFalse(result["success"])
        self.assertIn("timeout", result["error"])


class TestGetJobResult(unittest.TestCase):
    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.get")
    def test_returns_video_url_on_success(self, mock_get):
        mock_get.return_value = _response(
            {"video": {"url": "https://v2.fal.media/files/abc_output.mp4"}}
        )

        result = FalVideoService().get_job_result("req-123")

        self.assertTrue(result["success"])
        self.assertEqual(result["video_url"], "https://v2.fal.media/files/abc_output.mp4")
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://queue.fal.run/fal-ai/kling-video/requests/req-123",
        )

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.get")
    def test_missing_video_url_is_an_error(self, mock_get):
        mock_get.return_value = _response({"video": {}})

        result = FalVideoService().get_job_result("req-123")

        self.assertFalse(result["success"])

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.get")
    def test_network_error_never_raises(self, mock_get):
        mock_get.side_effect = ConnectionError("boom")

        result = FalVideoService().get_job_result("req-123")

        self.assertFalse(result["success"])


class TestDownloadVideo(unittest.TestCase):
    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.services.fal_video.requests.get")
    def test_writes_response_content_to_dest_path(self, mock_get, mock_file, mock_makedirs):
        mock_get.return_value = _response({})
        mock_get.return_value.content = b"fake-mp4-bytes"

        ok = FalVideoService().download_video(
            "https://v2.fal.media/files/abc_output.mp4", "/tmp/tasks/proj-1/clip_0.mp4"
        )

        self.assertTrue(ok)
        mock_file.assert_called_once_with("/tmp/tasks/proj-1/clip_0.mp4", "wb")
        mock_file().write.assert_called_once_with(b"fake-mp4-bytes")

    @patch("app.services.fal_video.config.app", _CONFIGURED)
    @patch("app.services.fal_video.requests.get")
    def test_network_error_returns_false_without_raising(self, mock_get):
        mock_get.side_effect = ConnectionError("boom")

        ok = FalVideoService().download_video("https://example.com/x.mp4", "/tmp/x.mp4")

        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
