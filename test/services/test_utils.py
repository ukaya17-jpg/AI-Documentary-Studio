import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.documentary_project import DocumentaryProject
from app.utils import utils


class TestSaveProjectSnapshot(unittest.TestCase):
    """ÖZELLİK A (kullanıcı onaylı): save_project_snapshot() burada, artık
    private değil -- default_pipeline.run_pipeline() KADAR, webui'nin de
    (kullanıcı bir script'i düzenleyip yeniden render ettiğinde) zaten
    tamamlanmış bir projeyi diske geri yazabilmesi için taşındı.
    """

    def setUp(self):
        self.task_id = "test-save-project-snapshot"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    def test_writes_valid_json_matching_the_model(self):
        project = DocumentaryProject(project_id=self.task_id, topic="Mars")
        utils.save_project_snapshot(project)

        snapshot_path = os.path.join(self.task_directory, "project.json")
        with open(snapshot_path, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["project_id"], self.task_id)
        self.assertEqual(saved["topic"], "Mars")

    @patch("builtins.open", side_effect=OSError("disk full"))
    def test_never_raises_on_write_failure(self, mock_open):
        project = DocumentaryProject(project_id=self.task_id, topic="Mars")
        utils.save_project_snapshot(project)  # must not raise


if __name__ == "__main__":
    unittest.main()
