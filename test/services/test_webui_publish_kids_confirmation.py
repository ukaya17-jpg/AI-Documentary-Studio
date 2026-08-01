import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"


def _button_by_key(app, key):
    return next((w for w in app.button if w.key == key), None)


def _checkbox_by_key(app, key):
    return next((w for w in app.checkbox if w.key == key), None)


@patch("app.services.upload_post.upload_post_service.is_configured", return_value=True)
@patch("app.services.upload_post.upload_post_service.platforms", ["tiktok"])
class TestPublishSectionKidsConfirmation(unittest.TestCase):
    """"Bao" planı (kullanıcı onaylı, ÇOCUK GÜVENLİĞİ): format == Format.kids
    olan projeler için, standart platform seçiminin ÜSTÜNE, ek bir zorunlu
    "videoyu izledim" onay kutusu -- Publish butonu bu onay olmadan asla
    aktif olmamalı. Diğer tüm formatlar (kids DIŞINDA) bu ek adımdan hiç
    etkilenmemeli -- regresyon garantisi.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tmp_dir, ignore_errors=True))

    def _project(self, fmt: str = "") -> dict:
        # _render_publish_section is only reached when final_video_path exists
        # on disk (see webui/Main.py's `if final_video_path and os.path.exists(...)`
        # gate right before it) -- a real (if fake-content) file is required.
        video_path = Path(self.tmp_dir) / "final.mp4"
        video_path.write_bytes(b"fake-mp4-bytes-for-test")
        project = {
            "topic": "A gentle bamboo forest walk",
            "final_video_path": str(video_path),
        }
        if fmt:
            project["format"] = fmt
        return project

    def test_kids_checkbox_absent_for_non_kids_project(self, *_mocks):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_last_project"] = self._project("educational")
        app.run()

        self.assertIsNone(_checkbox_by_key(app, "documentary_publish_kids_review_confirmed"))
        publish_button = _button_by_key(app, "documentary_publish_button")
        self.assertIsNotNone(publish_button)
        self.assertFalse(publish_button.disabled)

    def test_kids_checkbox_absent_when_format_missing(self, *_mocks):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_last_project"] = self._project("")
        app.run()

        self.assertIsNone(_checkbox_by_key(app, "documentary_publish_kids_review_confirmed"))
        publish_button = _button_by_key(app, "documentary_publish_button")
        self.assertFalse(publish_button.disabled)

    def test_kids_project_disables_publish_until_checkbox_confirmed(self, *_mocks):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_last_project"] = self._project("kids")
        app.run()

        checkbox = _checkbox_by_key(app, "documentary_publish_kids_review_confirmed")
        self.assertIsNotNone(checkbox)
        self.assertFalse(checkbox.value)
        publish_button = _button_by_key(app, "documentary_publish_button")
        self.assertTrue(publish_button.disabled)

    def test_kids_project_enables_publish_once_checkbox_confirmed(self, *_mocks):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_last_project"] = self._project("kids")
        app.session_state["documentary_publish_kids_review_confirmed"] = True
        app.run()

        publish_button = _button_by_key(app, "documentary_publish_button")
        self.assertFalse(publish_button.disabled)


if __name__ == "__main__":
    unittest.main()
