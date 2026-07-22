import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.script import Script
from app.services import seo_generator


class TestGenerateSeoMetadata(unittest.TestCase):
    @patch("app.services.seo_generator.llm.generate_social_metadata")
    def test_maps_social_metadata_result_to_seo_metadata(self, mock_generate_social_metadata):
        mock_generate_social_metadata.return_value = {
            "title": "The Fall of Rome",
            "caption": "How the mightiest empire in history collapsed.",
            "hashtags": ["#history", "#rome"],
        }
        script = Script(full_text="Rome fell in 476 AD.")
        seo = seo_generator.generate_seo_metadata("The Fall of Rome", script, language="en")

        self.assertEqual(seo.title, "The Fall of Rome")
        self.assertEqual(seo.description, "How the mightiest empire in history collapsed.")
        self.assertEqual(seo.hashtags, ["#history", "#rome"])
        mock_generate_social_metadata.assert_called_once_with(
            video_subject="The Fall of Rome",
            video_script="Rome fell in 476 AD.",
            language="en",
            platform="youtube_shorts",
        )


if __name__ == "__main__":
    unittest.main()
