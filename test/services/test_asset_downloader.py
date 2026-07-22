import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.asset import AssetCandidate, AssetPlan
from app.departments.production import asset_downloader


class TestDownloadAssets(unittest.TestCase):
    @patch("app.departments.production.asset_downloader.material.download_videos")
    def test_calls_legacy_download_videos_with_scene_ordered_terms(self, mock_download_videos):
        mock_download_videos.return_value = ["/tmp/a.mp4", "/tmp/b.mp4"]
        plan = AssetPlan(
            candidates=[
                AssetCandidate(scene_index=0, search_term="ancient ruins"),
                AssetCandidate(scene_index=1, search_term="battle field"),
            ]
        )
        result = asset_downloader.download_assets(plan, task_id="t1", audio_duration=20.0)

        mock_download_videos.assert_called_once()
        _, kwargs = mock_download_videos.call_args
        self.assertEqual(kwargs["search_terms"], ["ancient ruins", "battle field"])
        self.assertEqual(kwargs["task_id"], "t1")
        self.assertEqual(kwargs["audio_duration"], 20.0)
        self.assertTrue(kwargs["match_script_order"])
        self.assertEqual(result.downloaded_paths, ["/tmp/a.mp4", "/tmp/b.mp4"])

    @patch("app.departments.production.asset_downloader.material.download_videos")
    def test_skips_call_when_no_candidates(self, mock_download_videos):
        plan = AssetPlan(candidates=[])
        result = asset_downloader.download_assets(plan, task_id="t1", audio_duration=10.0)
        mock_download_videos.assert_not_called()
        self.assertEqual(result.downloaded_paths, [])


if __name__ == "__main__":
    unittest.main()
