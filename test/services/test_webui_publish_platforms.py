import ast
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"


def _find_assigned_list(tree: ast.AST, name: str) -> list:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"no top-level assignment named {name!r} found in {WEBUI_MAIN}")


class TestPublishSectionPlatforms(unittest.TestCase):
    """_render_publish_section's known_platforms is what the user actually
    sees as selectable checkboxes -- this locks in that Instagram (and
    TikTok/YouTube) are real, selectable options, independent of whatever
    upload_post_platforms happens to be configured as the default.
    """

    def test_known_platforms_include_instagram_tiktok_and_youtube(self):
        tree = ast.parse(WEBUI_MAIN.read_text(encoding="utf-8"))
        known_platforms = _find_assigned_list(tree, "known_platforms")

        self.assertIn("instagram", known_platforms)
        self.assertIn("tiktok", known_platforms)
        self.assertIn("youtube", known_platforms)


if __name__ == "__main__":
    unittest.main()
