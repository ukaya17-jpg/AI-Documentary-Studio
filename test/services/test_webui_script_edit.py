import json
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

ALL_LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")

NEW_KEYS = (
    "Documentary Edit Script",
    "Documentary Edit Script Help",
    "Documentary Edit Script Large Change Warning",
    "Documentary Edit Script Scene",
    "Documentary Edit Script Regenerate Button",
    "Documentary Edit Script Regenerating",
    "Documentary Edit Script Success",
    "Documentary Edit Script Failed",
)


def _translation(locale):
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def test_edit_script_keys_present_and_non_empty_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in NEW_KEYS:
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def _sample_project_with_script(base_dir: Path) -> dict:
    video_path = base_dir / "final.mp4"
    video_path.write_bytes(b"fake-mp4-bytes-for-test")
    return {
        "project_id": "edit-script-test",
        "topic": "The Fall of Rome",
        "final_video_path": str(video_path),
        "thumbnail_path": "",
        "thumbnail_variant_b_path": "",
        "research_plan": {"grounded": True},
        "script": {
            "full_text": "Rome began humbly.\n\nThen it all fell apart.",
            "lines": [
                {"scene_index": 0, "text": "Rome began humbly."},
                {"scene_index": 1, "text": "Then it all fell apart."},
            ],
        },
    }


def test_edit_script_section_shows_one_text_area_per_scene(tmp_path):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_last_project"] = _sample_project_with_script(tmp_path)
    app.run()

    assert not app.exception

    en = _translation("en")
    scene_areas = [
        w for w in app.text_area if w.label.startswith(en["Documentary Edit Script Scene"])
    ]
    assert len(scene_areas) == 2
    values = sorted(w.value for w in scene_areas)
    assert values == ["Rome began humbly.", "Then it all fell apart."]


def test_edit_script_section_shows_the_large_change_warning(tmp_path):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_last_project"] = _sample_project_with_script(tmp_path)
    app.run()

    assert not app.exception
    en = _translation("en")
    assert any(w.value == en["Documentary Edit Script Large Change Warning"] for w in app.warning)


def test_edit_script_section_hidden_when_project_has_no_script(tmp_path):
    project = _sample_project_with_script(tmp_path)
    del project["script"]

    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_last_project"] = project
    app.run()

    assert not app.exception
    en = _translation("en")
    assert not any(
        w.label.startswith(en["Documentary Edit Script Scene"]) for w in app.text_area
    )
