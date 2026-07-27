import json
import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from streamlit.util import calc_hash

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils import utils

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

_HISTORY_PAGE_HASH = calc_hash("history")

ALL_LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")

NEW_KEYS = (
    "Documentary Custom Tags",
    "Documentary Custom Tags Help",
    "Documentary Custom Tags Input",
    "Documentary Custom Tags Save",
    "Documentary Custom Tags Saved",
    "Documentary History Filter By Tags",
    "Documentary History No Match For Tags",
)


def _translation(locale):
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def test_custom_tags_keys_present_and_non_empty_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in NEW_KEYS:
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def _sample_project(base_dir: Path, *, project_id="tags-test", custom_tags=None) -> dict:
    video_path = base_dir / "final.mp4"
    video_path.write_bytes(b"fake-mp4-bytes-for-test")
    return {
        "project_id": project_id,
        "topic": "The Roman Empire",
        "final_video_path": str(video_path),
        "thumbnail_path": "",
        "thumbnail_variant_b_path": "",
        "research_plan": {"topic": "The Roman Empire", "grounded": True},
        "custom_tags": custom_tags or [],
    }


def test_documentary_studio_shows_custom_tags_input_prefilled(tmp_path):
    en = _translation("en")
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_last_project"] = _sample_project(
        tmp_path, custom_tags=["news", "ancient rome"]
    )
    app.run()

    assert not app.exception
    tags_input = next(
        w for w in app.text_input if w.label == en["Documentary Custom Tags Input"]
    )
    assert tags_input.value == "news, ancient rome"
    save_buttons = [w for w in app.button if w.label == en["Documentary Custom Tags Save"]]
    assert len(save_buttons) == 1


def test_documentary_studio_custom_tags_input_empty_when_no_tags(tmp_path):
    en = _translation("en")
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_last_project"] = _sample_project(tmp_path, custom_tags=[])
    app.run()

    assert not app.exception
    tags_input = next(
        w for w in app.text_input if w.label == en["Documentary Custom Tags Input"]
    )
    assert tags_input.value == ""


def test_saving_tags_trims_whitespace_and_drops_empty_entries(tmp_path):
    """Save butonu, virgülle ayrılmış girdiyi trim edip boşları atarak
    save_project_snapshot()'a doğru custom_tags listesini geçirmeli.

    GÖREV 1'den öğrenilen AppTest kısıtı burada da geçerli: Documentary
    Studio'nun Pacing selectbox'ı format_func'ında tr() çağırıyor (dolaylı
    olarak session_state okuyor) -- bu yüzden .set_value()/.click() zinciri
    yerine, hem metin girdisi hem de buton tıklaması TEK bir .run()'dan
    önce session_state'e önceden yazılıyor. Bunun kendi tuzağı var: buton
    handler'ı kendi içinde st.rerun() çağırıyor, ve preset edilen session_state
    bayrağı hiç temizlenmediği için (gerçek bir tıklamanın aksine) her rerun
    turunda "yeniden tıklanmış" görünüp SONSUZ DÖNGÜYE girer (bir defasında
    süreç bu yüzden kilitlenip öldürüldü) -- bu yüzden st.rerun() burada
    no-op'a patch'leniyor, tek script geçişi rerun tetiklemeden tamamlanıyor.
    """
    en = _translation("en")
    project = _sample_project(tmp_path, custom_tags=[])
    project_id = project["project_id"]

    with (
        patch.object(utils, "save_project_snapshot") as save_mock,
        patch("streamlit.rerun"),
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_last_project"] = project
        app.session_state[f"documentary_custom_tags_input_{project_id}"] = (
            " news ,  ancient rome ,, "
        )
        app.session_state[f"documentary_custom_tags_save_{project_id}"] = True
        app.run()

    assert not app.exception
    save_mock.assert_called_once()
    saved_project = save_mock.call_args[0][0]
    assert saved_project.custom_tags == ["news", "ancient rome"]
    assert any(item.value == en["Documentary Custom Tags Saved"] for item in app.success)


def _make_history_task(tasks_root: Path, task_id: str, topic: str, tags: list[str]) -> None:
    task_path = tasks_root / task_id
    task_path.mkdir()
    video_path = task_path / "final.mp4"
    video_path.write_bytes(b"fake-mp4-bytes-for-test")
    project = {
        "project_id": task_id,
        "topic": topic,
        "final_video_path": str(video_path),
        "thumbnail_path": "",
        "thumbnail_variant_b_path": "",
        "custom_tags": tags,
    }
    (task_path / "project.json").write_text(json.dumps(project), encoding="utf-8")


def test_history_page_hides_tag_filter_when_no_project_has_tags(tmp_path):
    _make_history_task(tmp_path, "task-1", "The Roman Empire", [])

    en = _translation("en")
    with patch.object(utils, "task_dir", return_value=str(tmp_path)):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app._page_hash = _HISTORY_PAGE_HASH
        app.session_state["ui_language"] = "en"
        app.run()

    assert not app.exception
    assert not any(
        w.label == en["Documentary History Filter By Tags"] for w in app.multiselect
    )


def test_history_page_filters_by_selected_tags(tmp_path):
    _make_history_task(tmp_path, "task-rome", "The Roman Empire", ["ancient", "europe"])
    _make_history_task(tmp_path, "task-egypt", "Ancient Egypt", ["ancient", "africa"])
    _make_history_task(tmp_path, "task-space", "The Moon Landing", ["space"])

    en = _translation("en")
    with patch.object(utils, "task_dir", return_value=str(tmp_path)):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app._page_hash = _HISTORY_PAGE_HASH
        app.session_state["ui_language"] = "en"
        app.run()

        assert not app.exception
        tag_filter = next(
            w for w in app.multiselect if w.label == en["Documentary History Filter By Tags"]
        )
        assert sorted(tag_filter.options) == ["africa", "ancient", "europe", "space"]

        tag_filter.set_value(["space"]).run()

    assert not app.exception
    markdown_text = " ".join(m.value for m in app.markdown)
    assert "The Moon Landing" in markdown_text
    assert "The Roman Empire" not in markdown_text
    assert "Ancient Egypt" not in markdown_text


