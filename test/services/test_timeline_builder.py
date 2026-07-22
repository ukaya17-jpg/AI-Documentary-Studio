import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.asset import AssetCandidate, AssetPlan
from app.models.audio import AudioTrack
from app.services import timeline_builder
from app.utils import utils


class TestBuildTimeline(unittest.TestCase):
    def setUp(self):
        self.task_id = "test-timeline-builder"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    @patch("app.services.timeline_builder.video.combine_videos")
    def test_calls_combine_videos_and_builds_timeline(self, mock_combine_videos):
        mock_combine_videos.side_effect = lambda combined_video_path, **kwargs: combined_video_path

        asset_plan = AssetPlan(
            candidates=[
                AssetCandidate(scene_index=0, search_term="ruins"),
                AssetCandidate(scene_index=1, search_term="battle"),
            ],
            downloaded_paths=["/tmp/ruins.mp4", "/tmp/battle.mp4"],
        )
        audio_track = AudioTrack(voice_file="/tmp/audio.mp3", duration_seconds=20.0)

        timeline = timeline_builder.build_timeline(asset_plan, audio_track, self.task_id)

        mock_combine_videos.assert_called_once()
        _, kwargs = mock_combine_videos.call_args
        self.assertEqual(kwargs["video_paths"], ["/tmp/ruins.mp4", "/tmp/battle.mp4"])
        self.assertEqual(kwargs["audio_file"], "/tmp/audio.mp3")
        self.assertTrue(timeline.combined_video_path.endswith("combined.mp4"))
        self.assertEqual(timeline.total_duration, 20.0)
        self.assertEqual(len(timeline.clips), 2)
        self.assertEqual(timeline.clips[0].scene_index, 0)
        self.assertEqual(timeline.clips[0].video_path, "/tmp/ruins.mp4")


if __name__ == "__main__":
    unittest.main()
