import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image, ImageDraw, ImageFont

from app.departments.growth import thumbnail_generator
from app.models.seo import SeoMetadata
from app.utils import utils

_FONT_PATH = os.path.join(utils.font_dir(), "BeVietnamPro-Bold.ttf")


def _draw_and_font(font_size=60):
    img = Image.new("RGB", (1080, 1920))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(_FONT_PATH, font_size)
    return draw, font


class TestFontScales(unittest.TestCase):
    def test_starts_at_full_scale_and_ends_at_floor(self):
        scales = thumbnail_generator._font_scales()
        self.assertEqual(scales[0], 1.0)
        self.assertEqual(scales[-1], thumbnail_generator._MIN_FONT_SCALE)

    def test_is_monotonically_decreasing(self):
        scales = thumbnail_generator._font_scales()
        self.assertEqual(scales, sorted(scales, reverse=True))

    def test_never_goes_below_floor(self):
        scales = thumbnail_generator._font_scales()
        self.assertTrue(all(s >= thumbnail_generator._MIN_FONT_SCALE for s in scales))


class TestWrapText(unittest.TestCase):
    def test_short_text_fits_on_one_line(self):
        draw, font = _draw_and_font(font_size=60)
        lines = thumbnail_generator._wrap_text(draw, "Short Title", font, max_width=900)
        self.assertEqual(lines, ["Short Title"])

    def test_long_text_wraps_into_multiple_lines(self):
        draw, font = _draw_and_font(font_size=90)
        title = "Rome Didn't Fall Overnight-Here's What Cracked the Empire"
        lines = thumbnail_generator._wrap_text(draw, title, font, max_width=918)
        self.assertGreater(len(lines), 1)
        # No word should be lost across the wrap.
        self.assertEqual(" ".join(lines).split(), title.split())

    def test_smaller_font_produces_fewer_or_equal_lines(self):
        draw, _ = _draw_and_font()
        title = "Rome Didn't Fall Overnight-Here's What Cracked the Empire"
        big_font = ImageFont.truetype(_FONT_PATH, 90)
        small_font = ImageFont.truetype(_FONT_PATH, 54)  # 90 * 0.6 floor
        big_lines = thumbnail_generator._wrap_text(draw, title, big_font, max_width=918)
        small_lines = thumbnail_generator._wrap_text(draw, title, small_font, max_width=918)
        self.assertLessEqual(len(small_lines), len(big_lines))


class TestTruncateWithEllipsis(unittest.TestCase):
    def test_short_line_just_gets_ellipsis_appended(self):
        draw, font = _draw_and_font(font_size=60)
        result = thumbnail_generator._truncate_with_ellipsis(draw, "Short", font, max_width=900)
        self.assertEqual(result, "Short...")

    def test_long_line_is_shortened_to_fit(self):
        draw, font = _draw_and_font(font_size=90)
        long_line = "What Cracked the Roman Empire Completely Apart"
        max_width = 500
        result = thumbnail_generator._truncate_with_ellipsis(draw, long_line, font, max_width)
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(draw.textlength(result, font=font), max_width)
        self.assertLess(len(result), len(long_line) + 3)

    def test_falls_back_to_bare_ellipsis_when_nothing_fits(self):
        draw, font = _draw_and_font(font_size=90)
        result = thumbnail_generator._truncate_with_ellipsis(draw, "Word", font, max_width=1)
        self.assertEqual(result, "...")


class TestOverlayTitleRealRendering(unittest.TestCase):
    """Real PIL rendering (real font, real image) -- no mocks -- to prove the
    shrink-and-retry + ellipsis fallback actually produce a valid image for
    both a realistic long title and an extreme one."""

    def setUp(self):
        self.tmp_dir = "/tmp/test-thumbnail-generator-overlay"
        os.makedirs(self.tmp_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_frame(self, name):
        path = os.path.join(self.tmp_dir, name)
        Image.new("RGB", (1080, 1920), color=(80, 80, 80)).save(path)
        return path

    @patch("app.departments.growth.thumbnail_generator.config")
    def test_realistic_long_title_renders_without_crashing(self, mock_config):
        mock_config.ui.get.return_value = "BeVietnamPro-Bold.ttf"
        path = self._make_frame("real_title.png")
        ok = thumbnail_generator._overlay_title(
            path, "Rome Didn't Fall Overnight-Here's What Cracked the Empire"
        )
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(path))
        with Image.open(path) as img:
            self.assertEqual(img.size, (1080, 1920))

    @patch("app.departments.growth.thumbnail_generator.config")
    def test_extreme_title_falls_back_to_ellipsis_without_crashing(self, mock_config):
        mock_config.ui.get.return_value = "BeVietnamPro-Bold.ttf"
        path = self._make_frame("extreme_title.png")
        extreme_title = (
            "This Is An Absurdly Long Documentary Title That No Amount Of Font "
            "Shrinking Could Ever Make Fit Into Three Reasonable Lines No Matter "
            "What We Try Because It Just Keeps Going On And On"
        )
        ok = thumbnail_generator._overlay_title(path, extreme_title)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(path))


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
    @patch("app.departments.growth.thumbnail_generator._extract_frame_at_fraction", return_value=True)
    def test_returns_path_when_frame_and_overlay_succeed(self, mock_extract, mock_overlay):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail(
                "/tmp/combined.mp4", SeoMetadata(title="The Fall of Rome"), self.task_id
            )
        self.assertTrue(result.endswith("thumbnail.png"))
        mock_extract.assert_called_once()
        mock_overlay.assert_called_once_with(result, "The Fall of Rome")

    @patch("app.departments.growth.thumbnail_generator._extract_frame_at_fraction", return_value=False)
    def test_returns_empty_string_when_frame_extraction_fails(self, mock_extract):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail(
                "/tmp/combined.mp4", SeoMetadata(title="X"), self.task_id
            )
        self.assertEqual(result, "")

    @patch("app.departments.growth.thumbnail_generator._overlay_title", return_value=False)
    @patch("app.departments.growth.thumbnail_generator._extract_frame_at_fraction", return_value=True)
    def test_returns_empty_string_when_overlay_fails(self, mock_extract, mock_overlay):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail(
                "/tmp/combined.mp4", SeoMetadata(title="X"), self.task_id
            )
        self.assertEqual(result, "")

    @patch("app.departments.growth.thumbnail_generator._overlay_title", return_value=True)
    @patch("app.departments.growth.thumbnail_generator._extract_frame_at_fraction", return_value=True)
    def test_handles_missing_seo(self, mock_extract, mock_overlay):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail("/tmp/combined.mp4", None, self.task_id)
        self.assertTrue(result.endswith("thumbnail.png"))
        mock_overlay.assert_called_once_with(result, "")


class TestExtractFrameAtFraction(unittest.TestCase):
    @patch("app.departments.growth.thumbnail_generator.VideoFileClip")
    def test_saves_frame_at_half_duration_by_default_fraction(self, mock_video_file_clip):
        mock_clip = MagicMock()
        mock_clip.duration = 20.0
        mock_video_file_clip.return_value = mock_clip

        result = thumbnail_generator._extract_frame_at_fraction(
            "/tmp/combined.mp4", "/tmp/out.png", 0.5
        )

        self.assertTrue(result)
        mock_clip.save_frame.assert_called_once_with("/tmp/out.png", t=10.0)
        mock_clip.close.assert_called_once()

    @patch("app.departments.growth.thumbnail_generator.VideoFileClip")
    def test_saves_frame_at_a_quarter_duration(self, mock_video_file_clip):
        mock_clip = MagicMock()
        mock_clip.duration = 20.0
        mock_video_file_clip.return_value = mock_clip

        result = thumbnail_generator._extract_frame_at_fraction(
            "/tmp/combined.mp4", "/tmp/out.png", 0.25
        )

        self.assertTrue(result)
        mock_clip.save_frame.assert_called_once_with("/tmp/out.png", t=5.0)

    @patch("app.departments.growth.thumbnail_generator.VideoFileClip")
    def test_returns_false_on_exception(self, mock_video_file_clip):
        mock_video_file_clip.side_effect = Exception("corrupt file")
        result = thumbnail_generator._extract_frame_at_fraction(
            "/tmp/combined.mp4", "/tmp/out.png", 0.5
        )
        self.assertFalse(result)


class TestGenerateThumbnailVariantB(unittest.TestCase):
    def setUp(self):
        self.task_id = "variant-b-task"
        self.addCleanup(
            lambda: shutil.rmtree(utils.task_dir(self.task_id), ignore_errors=True)
        )

    @patch("app.departments.growth.thumbnail_generator._overlay_title", return_value=True)
    @patch(
        "app.departments.growth.thumbnail_generator._extract_frame_at_fraction",
        return_value=True,
    )
    def test_uses_a_different_filename_and_earlier_fraction_than_variant_a(
        self, mock_extract, mock_overlay
    ):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail_variant_b(
                "/tmp/combined.mp4", SeoMetadata(title="The Fall of Rome"), self.task_id
            )

        self.assertTrue(result.endswith("thumbnail_b.png"))
        _video_path, _output_path, fraction = mock_extract.call_args[0]
        self.assertEqual(fraction, thumbnail_generator._VARIANT_B_FRAME_FRACTION)
        self.assertLess(thumbnail_generator._VARIANT_B_FRAME_FRACTION, 0.5)
        mock_overlay.assert_called_once_with(result, "The Fall of Rome")

    @patch(
        "app.departments.growth.thumbnail_generator._extract_frame_at_fraction",
        return_value=False,
    )
    def test_returns_empty_string_when_frame_extraction_fails(self, mock_extract):
        with patch("os.path.exists", return_value=True):
            result = thumbnail_generator.generate_thumbnail_variant_b(
                "/tmp/combined.mp4", SeoMetadata(title="X"), self.task_id
            )
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
