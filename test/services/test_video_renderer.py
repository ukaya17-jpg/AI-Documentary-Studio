import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.audio import AudioTrack
from app.models.schema import VideoParams
from app.models.timeline import Timeline
from app.services import video_renderer
from app.utils import utils


class TestRenderFinalVideo(unittest.TestCase):
    def setUp(self):
        self.task_id = "test-video-renderer"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    @patch("app.services.video_renderer.video.generate_video", return_value=True)
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

    @patch("app.services.video_renderer.logger.warning")
    @patch("app.services.video_renderer.video.generate_video", return_value=False)
    def test_logs_warning_when_bgm_mix_fails(self, mock_generate_video, mock_log_warning):
        timeline = Timeline(combined_video_path="/tmp/combined.mp4")
        audio_track = AudioTrack(voice_file="/tmp/audio.mp3")
        params = VideoParams(video_subject="Rome", bgm_type="random")

        video_renderer.render_final_video(timeline, audio_track, self.task_id, params)

        mock_log_warning.assert_called_once()

    @patch("app.services.video_renderer.logger.warning")
    @patch("app.services.video_renderer.video.generate_video", return_value=True)
    def test_no_warning_when_bgm_mix_succeeds(self, mock_generate_video, mock_log_warning):
        timeline = Timeline(combined_video_path="/tmp/combined.mp4")
        audio_track = AudioTrack(voice_file="/tmp/audio.mp3")
        params = VideoParams(video_subject="Rome", bgm_type="random")

        video_renderer.render_final_video(timeline, audio_track, self.task_id, params)

        mock_log_warning.assert_not_called()


if __name__ == "__main__":
    unittest.main()
