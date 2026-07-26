import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.fal_video import FalVideoService

_CONFIGURED = {
    "fal_api_key": "test-fal-key",
    "fal_kling_model": "fal-ai/kling-video/v1.0/standard/text-to-video",
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
    def test_uses_configured_model_and_default_fallback(self):
        self.assertEqual(
            FalVideoService().model, "fal-ai/kling-video/v1.0/standard/text-to-video"
        )
        with patch("app.services.fal_video.config.app", {"fal_api_key": "k"}):
            # fal_kling_model not set at all -- must fall back to the module default.
            from app.services.fal_video import DEFAULT_KLING_MODEL

            self.assertEqual(FalVideoService().model, DEFAULT_KLING_MODEL)


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
            "https://queue.fal.run/fal-ai/kling-video/v1.0/standard/text-to-video",
        )
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Key test-fal-key")
        self.assertEqual(call.kwargs["json"]["prompt"], "a wide shot of ancient ruins")
        self.assertEqual(call.kwargs["json"]["duration"], "10")
        self.assertEqual(call.kwargs["json"]["aspect_ratio"], "9:16")

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
        self.assertIn("req-123/status", mock_get.call_args.args[0])

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
