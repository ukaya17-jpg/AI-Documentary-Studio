import ast
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.models.audio import AudioTrack
from app.models.schema import VideoParams
from app.models.timeline import Timeline
from app.departments.production import video_renderer
from app.utils import utils

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"


def _webui_default_subtitle_settings() -> dict:
    """Read webui/Main.py's DEFAULT_SUBTITLE_SETTINGS via AST, without
    importing/running Main.py (it executes _render_application() at import
    time and isn't safe to import from a non-Streamlit process)."""
    tree = ast.parse(WEBUI_MAIN.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "DEFAULT_SUBTITLE_SETTINGS"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"no DEFAULT_SUBTITLE_SETTINGS assignment found in {WEBUI_MAIN}")


class TestDefaultSubtitleFontStaysInSync(unittest.TestCase):
    """GÖREV 8a (gece oturumu): webui's DEFAULT_SUBTITLE_SETTINGS and
    video_renderer's _DEFAULT_SUBTITLE_SETTINGS used to disagree on
    font_name (MicrosoftYaHeiBold.ttc vs BeVietnamPro-Bold.ttf) -- on a
    fresh install with no explicit config.toml [ui].font_name, the UI's
    implied default and the actually-rendered font would silently differ.
    Both now default to the same font; this locks that in.
    """

    def test_webui_and_video_renderer_font_defaults_match(self):
        webui_default = _webui_default_subtitle_settings()["font_name"]
        self.assertEqual(webui_default, video_renderer._DEFAULT_SUBTITLE_SETTINGS["font_name"])

    def test_default_font_is_the_project_standard_sans_serif(self):
        # Pin the actual value too, not just "the two agree" -- a
        # regression where both drift back to the CJK font together
        # wouldn't be caught by the equality check above.
        self.assertEqual(
            video_renderer._DEFAULT_SUBTITLE_SETTINGS["font_name"], "BeVietnamPro-Bold.ttf"
        )


class TestRenderFinalVideo(unittest.TestCase):
    def setUp(self):
        self.task_id = "test-video-renderer"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    @patch("app.departments.production.video_renderer.video.generate_video", return_value=True)
    def test_calls_generate_video_with_expected_paths(self, mock_generate_video):
        timeline = Timeline(combined_video_path="/tmp/combined.mp4")
        audio_track = AudioTrack(voice_file="/tmp/audio.mp3", subtitle_file="/tmp/subtitle.srt")
        params = VideoParams(video_subject="Rome")

        output_file = video_renderer.render_final_video(timeline, audio_track, self.task_id, params)

        mock_generate_video.assert_called_once()
        _, kwargs = mock_generate_video.call_args
        self.assertEqual(kwargs["video_path"], "/tmp/combined.mp4")
        self.assertEqual(kwargs["audio_path"], "/tmp/audio.mp3")
        self.assertEqual(kwargs["subtitle_path"], "/tmp/subtitle.srt")
        self.assertTrue(output_file.endswith("final.mp4"))

    @patch("app.departments.production.video_renderer.logger.warning")
    @patch("app.departments.production.video_renderer.video.generate_video", return_value=False)
    def test_logs_warning_when_bgm_mix_fails(self, mock_generate_video, mock_log_warning):
        timeline = Timeline(combined_video_path="/tmp/combined.mp4")
        audio_track = AudioTrack(voice_file="/tmp/audio.mp3")
        params = VideoParams(video_subject="Rome", bgm_type="random")

        video_renderer.render_final_video(timeline, audio_track, self.task_id, params)

        mock_log_warning.assert_called_once()

    @patch("app.departments.production.video_renderer.logger.warning")
    @patch("app.departments.production.video_renderer.video.generate_video", return_value=True)
    def test_no_warning_when_bgm_mix_succeeds(self, mock_generate_video, mock_log_warning):
        timeline = Timeline(combined_video_path="/tmp/combined.mp4")
        audio_track = AudioTrack(voice_file="/tmp/audio.mp3")
        params = VideoParams(video_subject="Rome", bgm_type="random")

        video_renderer.render_final_video(timeline, audio_track, self.task_id, params)

        mock_log_warning.assert_not_called()


class TestBuildVideoParams(unittest.TestCase):
    def setUp(self):
        self._saved_ui = dict(config.ui)

    def tearDown(self):
        config.ui.clear()
        config.ui.update(self._saved_ui)

    def test_uses_configured_subtitle_appearance(self):
        config.ui["font_name"] = "MicrosoftYaHeiBold.ttc"
        config.ui["text_fore_color"] = "#00FF00"
        config.ui["font_size"] = 42
        config.ui["subtitle_background_enabled"] = True
        config.ui["subtitle_background_color"] = "#123456"
        config.ui["rounded_subtitle_background"] = True

        params = video_renderer.build_video_params(
            topic="Rome", video_aspect="9:16", voice_name="en-US-JennyNeural"
        )

        self.assertEqual(params.font_name, "MicrosoftYaHeiBold.ttc")
        self.assertEqual(params.text_fore_color, "#00FF00")
        self.assertEqual(params.font_size, 42)
        self.assertEqual(params.text_background_color, "#123456")
        self.assertTrue(params.rounded_subtitle_background)

    def test_no_background_color_when_subtitle_background_disabled(self):
        config.ui["subtitle_background_enabled"] = False
        config.ui["subtitle_background_color"] = "#123456"

        params = video_renderer.build_video_params(
            topic="Rome", video_aspect="9:16", voice_name="en-US-JennyNeural"
        )

        self.assertFalse(params.text_background_color)

    def test_falls_back_to_defaults_when_unset(self):
        config.ui.clear()

        params = video_renderer.build_video_params(
            topic="Rome", video_aspect="9:16", voice_name="en-US-JennyNeural"
        )

        self.assertEqual(params.font_name, "BeVietnamPro-Bold.ttf")
        self.assertEqual(params.text_fore_color, "#FFFFFF")
        self.assertEqual(params.font_size, 60)


if __name__ == "__main__":
    unittest.main()
