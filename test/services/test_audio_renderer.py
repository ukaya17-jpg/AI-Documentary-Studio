import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.script import Script
from app.departments.production import audio_renderer
from app.utils import utils


class TestRenderNarration(unittest.TestCase):
    def setUp(self):
        self.task_id = "test-audio-renderer"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    @patch("app.departments.production.audio_renderer.voice.create_subtitle")
    @patch("app.departments.production.audio_renderer.voice.get_audio_duration", return_value=12.5)
    @patch("app.departments.production.audio_renderer.voice.tts")
    @patch("app.departments.production.audio_renderer.voice.parse_voice_name", side_effect=lambda v: v)
    def test_builds_audio_track_from_tts_result(
        self, mock_parse_voice_name, mock_tts, mock_get_duration, mock_create_subtitle
    ):
        mock_tts.return_value = MagicMock()

        def fake_create_subtitle(sub_maker, text, subtitle_file):
            Path(subtitle_file).write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n")

        mock_create_subtitle.side_effect = fake_create_subtitle

        script = Script(full_text="Rome was not built in a day.")
        track = audio_renderer.render_narration(script, self.task_id, "tr-TR-AhmetNeural")

        self.assertEqual(track.voice_name, "tr-TR-AhmetNeural")
        self.assertTrue(track.voice_file.endswith("audio.mp3"))
        self.assertTrue(track.subtitle_file.endswith("subtitle.srt"))
        self.assertEqual(track.duration_seconds, 12.5)
        mock_tts.assert_called_once()
        _, kwargs = mock_tts.call_args
        self.assertEqual(kwargs["text"], "Rome was not built in a day.")

    @patch("app.departments.production.audio_renderer.voice.tts", return_value=None)
    @patch("app.departments.production.audio_renderer.voice.parse_voice_name", side_effect=lambda v: v)
    def test_raises_when_tts_fails(self, mock_parse_voice_name, mock_tts):
        script = Script(full_text="Text")
        with self.assertRaises(RuntimeError):
            audio_renderer.render_narration(script, self.task_id, "tr-TR-AhmetNeural")


if __name__ == "__main__":
    unittest.main()
