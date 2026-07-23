import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.departments.growth import publisher
from app.models.documentary_project import DocumentaryProject
from app.models.seo import SeoMetadata


def _project(**overrides):
    defaults = dict(
        project_id="p1",
        topic="How Rainbows Form",
        final_video_path="/fake/video.mp4",
        seo=SeoMetadata(title="Rainbow Science", description="A short explainer.", hashtags=["#science", "#rainbow"]),
    )
    defaults.update(overrides)
    return DocumentaryProject(**defaults)


class TestPublishProjectPreconditions(unittest.TestCase):
    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=False)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_unconfigured_service_returns_early_without_calling_cross_post(self, mock_cross_post, _configured):
        result = publisher.publish_project(_project())

        mock_cross_post.assert_not_called()
        self.assertFalse(result.success)
        self.assertIn("not configured", result.error)

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_missing_final_video_path_returns_early(self, mock_cross_post, _configured):
        result = publisher.publish_project(_project(final_video_path=""))

        mock_cross_post.assert_not_called()
        self.assertFalse(result.success)
        self.assertIn("No final video", result.error)

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_does_not_mutate_project(self, mock_cross_post, _configured):
        mock_cross_post.return_value = {"success": True, "request_id": "abc123"}
        project = _project()

        publisher.publish_project(project, platforms=["tiktok"])

        self.assertIsNone(project.publish_result)


class TestPublishProjectPayload(unittest.TestCase):
    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.upload_post_service.platforms", ["tiktok", "instagram"])
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_defaults_platforms_to_configured_list_when_none_given(self, mock_cross_post, *_mocks):
        mock_cross_post.return_value = {"success": True, "request_id": "abc123"}

        result = publisher.publish_project(_project(), platforms=None)

        self.assertEqual(mock_cross_post.call_args.kwargs["platforms"], ["tiktok", "instagram"])
        self.assertEqual(result.platforms, ["tiktok", "instagram"])

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_uses_seo_title_description_and_hashtags(self, mock_cross_post, _configured):
        mock_cross_post.return_value = {"success": True, "request_id": "abc123"}

        publisher.publish_project(_project(), platforms=["youtube"])

        kwargs = mock_cross_post.call_args.kwargs
        self.assertEqual(kwargs["title"], "Rainbow Science")
        self.assertEqual(kwargs["youtube_extra"]["youtube_title"], "Rainbow Science")
        self.assertEqual(kwargs["youtube_extra"]["youtube_description"], "A short explainer.")
        self.assertEqual(kwargs["youtube_extra"]["tags"], ["#science", "#rainbow"])

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_falls_back_to_topic_when_seo_missing(self, mock_cross_post, _configured):
        mock_cross_post.return_value = {"success": True, "request_id": "abc123"}

        publisher.publish_project(_project(seo=None), platforms=["tiktok"])

        self.assertEqual(mock_cross_post.call_args.kwargs["title"], "How Rainbows Form")

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_youtube_extra_omitted_when_youtube_not_in_platforms(self, mock_cross_post, _configured):
        mock_cross_post.return_value = {"success": True, "request_id": "abc123"}

        publisher.publish_project(_project(), platforms=["tiktok", "instagram"])

        self.assertIsNone(mock_cross_post.call_args.kwargs["youtube_extra"])

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_instagram_only_publish_succeeds_with_no_youtube_extra(self, mock_cross_post, _configured):
        # Instagram-only requests should behave exactly like tiktok-only ones:
        # generic title, no youtube_extra, platforms passed through as-is.
        mock_cross_post.return_value = {"success": True, "request_id": "ig-req-1"}

        result = publisher.publish_project(_project(), platforms=["instagram"])

        kwargs = mock_cross_post.call_args.kwargs
        self.assertEqual(kwargs["platforms"], ["instagram"])
        self.assertEqual(kwargs["title"], "Rainbow Science")
        self.assertIsNone(kwargs["youtube_extra"])
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "ig-req-1")
        self.assertEqual(result.platforms, ["instagram"])

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_instagram_combined_with_youtube_still_gets_youtube_extra(self, mock_cross_post, _configured):
        # Mixed platform lists (instagram + youtube) must still populate
        # youtube_extra -- instagram itself never blocks or alters it.
        mock_cross_post.return_value = {"success": True, "request_id": "mixed-req-1"}

        publisher.publish_project(_project(), platforms=["instagram", "youtube"])

        kwargs = mock_cross_post.call_args.kwargs
        self.assertEqual(kwargs["platforms"], ["instagram", "youtube"])
        self.assertIsNotNone(kwargs["youtube_extra"])
        self.assertEqual(kwargs["youtube_extra"]["youtube_title"], "Rainbow Science")

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch(
        "app.departments.growth.publisher.upload_post.upload_post_service.youtube_privacy_status",
        "public",
    )
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_youtube_privacy_status_param_overrides_config_default(self, mock_cross_post, *_mocks):
        mock_cross_post.return_value = {"success": True, "request_id": "abc123"}

        publisher.publish_project(_project(), platforms=["youtube"], youtube_privacy_status="private")

        self.assertEqual(mock_cross_post.call_args.kwargs["youtube_extra"]["privacyStatus"], "private")

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch(
        "app.departments.growth.publisher.upload_post.upload_post_service.youtube_privacy_status",
        "unlisted",
    )
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_youtube_privacy_status_falls_back_to_config_when_not_given(self, mock_cross_post, *_mocks):
        mock_cross_post.return_value = {"success": True, "request_id": "abc123"}

        publisher.publish_project(_project(), platforms=["youtube"], youtube_privacy_status=None)

        self.assertEqual(mock_cross_post.call_args.kwargs["youtube_extra"]["privacyStatus"], "unlisted")


class TestPublishProjectResult(unittest.TestCase):
    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_success_result_carries_request_id_and_platforms(self, mock_cross_post, _configured):
        mock_cross_post.return_value = {"success": True, "request_id": "abc123"}

        result = publisher.publish_project(_project(), platforms=["tiktok"])

        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "abc123")
        self.assertEqual(result.platforms, ["tiktok"])
        self.assertTrue(result.published_at)

    @patch("app.departments.growth.publisher.upload_post.upload_post_service.is_configured", return_value=True)
    @patch("app.departments.growth.publisher.upload_post.cross_post_video")
    def test_failed_cross_post_returns_failure_result(self, mock_cross_post, _configured):
        mock_cross_post.return_value = {"success": False, "message": "quota exceeded"}

        result = publisher.publish_project(_project(), platforms=["tiktok"])

        self.assertFalse(result.success)
        self.assertEqual(result.error, "quota exceeded")


if __name__ == "__main__":
    unittest.main()
