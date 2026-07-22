import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.departments.growth import thumbnail_generator
from app.models.seo import SeoMetadata
from app.utils import utils


class TestGenerateThumbnail(unittest.TestCase):
    def setUp(self):
        self.task_id = "test-thumbnail-generator"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    def test_returns_empty_string_when_video_missing(self):
        result = thumbnail_generator.generate_thumbnail(
            "/tmp/does-not-exist.mp4", SeoMetadata(title="X"), self.task_id
        )
        self.assertEqual(result, "")

    @patch("app.departments.growth.thumbnail_generator._overlay_title", return_value=True)
    @patch("app.departments.growth.thumbnail_generator._extract_middle_frame", return_value=True)
    def test_returns_path_when_frame_and_overlay_succeed(self, mock_extract, mock_overlay):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail(
                "/tmp/combined.mp4", SeoMetadata(title="The Fall of Rome"), self.task_id
            )
        self.assertTrue(result.endswith("thumbnail.png"))
        mock_extract.assert_called_once()
        mock_overlay.assert_called_once_with(result, "The Fall of Rome")

    @patch("app.departments.growth.thumbnail_generator._extract_middle_frame", return_value=False)
    def test_returns_empty_string_when_frame_extraction_fails(self, mock_extract):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail(
                "/tmp/combined.mp4", SeoMetadata(title="X"), self.task_id
            )
        self.assertEqual(result, "")

    @patch("app.departments.growth.thumbnail_generator._overlay_title", return_value=False)
    @patch("app.departments.growth.thumbnail_generator._extract_middle_frame", return_value=True)
    def test_returns_empty_string_when_overlay_fails(self, mock_extract, mock_overlay):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail(
                "/tmp/combined.mp4", SeoMetadata(title="X"), self.task_id
            )
        self.assertEqual(result, "")

    @patch("app.departments.growth.thumbnail_generator._overlay_title", return_value=True)
    @patch("app.departments.growth.thumbnail_generator._extract_middle_frame", return_value=True)
    def test_handles_missing_seo(self, mock_extract, mock_overlay):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail("/tmp/combined.mp4", None, self.task_id)
        self.assertTrue(result.endswith("thumbnail.png"))
        mock_overlay.assert_called_once_with(result, "")


class TestExtractMiddleFrame(unittest.TestCase):
    @patch("app.departments.growth.thumbnail_generator.VideoFileClip")
    def test_saves_frame_at_half_duration(self, mock_video_file_clip):
        mock_clip = MagicMock()
        mock_clip.duration = 20.0
        mock_video_file_clip.return_value = mock_clip

        result = thumbnail_generator._extract_middle_frame("/tmp/combined.mp4", "/tmp/out.png")

        self.assertTrue(result)
        mock_clip.save_frame.assert_called_once_with("/tmp/out.png", t=10.0)
        mock_clip.close.assert_called_once()

    @patch("app.departments.growth.thumbnail_generator.VideoFileClip")
    def test_returns_false_on_exception(self, mock_video_file_clip):
        mock_video_file_clip.side_effect = Exception("corrupt file")
        result = thumbnail_generator._extract_middle_frame("/tmp/combined.mp4", "/tmp/out.png")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
