import ast
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from loguru import logger
from PIL import Image
from streamlit.testing.v1 import AppTest
from streamlit.util import calc_hash

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils import utils

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

# Geçmiş Üretimler (Faz 4) sadece "history" url_path'inde yaşıyor;
# Documentary Studio varsayılan sayfa olduğu için (Faz 2) onun testleri
# _page_hash ayarlamadan çalışıyor. Aynı desen test_webui_bgm.py'deki
# _LEGACY_PAGE_HASH ("classic") için de kullanılıyor -- AppTest.switch_page()
# fonksiyon tabanlı st.navigation sayfalarını desteklemiyor.
_HISTORY_PAGE_HASH = calc_hash("history")

EN_TRANSLATION = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))[
    "Translation"
]


# -----------------------------------------------------------------------------
# _scan_history_projects / _safe_load_project_snapshot: Streamlit'siz izole
# birim testler. test_webui_task_history.py'deki _load_task_history_helpers
# ile aynı AST-çıkarma deseni -- Main.py'yi doğrudan import etmek tüm sayfa
# render zincirini çalıştırır, testler yalnızca hedef fonksiyonları derliyor.
# -----------------------------------------------------------------------------

_SCAN_HELPER_NAMES = {"_safe_load_project_snapshot", "_scan_history_projects"}
_SCAN_CONSTANT_NAMES = {"_HISTORY_PROJECTS_LIMIT"}


def _load_history_scan_helpers(tasks_root):
    """_scan_history_projects'in utils.task_dir() bağımlılığını, gerçek
    storage/tasks/ yerine verilen tasks_root'a sabitleyen bir stub ile
    değiştirerek izole yükler.
    """
    tree = ast.parse(WEBUI_MAIN.read_text(encoding="utf-8"))
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in _SCAN_CONSTANT_NAMES
            for target in node.targets
        ):
            selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in _SCAN_HELPER_NAMES:
            selected_nodes.append(node)

    namespace = {
        "os": os,
        "json": json,
        "logger": logger,
        "utils": SimpleNamespace(task_dir=lambda: str(tasks_root)),
    }
    module = ast.fix_missing_locations(ast.Module(body=selected_nodes, type_ignores=[]))
    exec(compile(module, str(WEBUI_MAIN), "exec"), namespace)
    return namespace


def _make_task(tasks_root: Path, task_id: str, *, project=None, has_video=True, mtime=None):
    """Bir görev klasörü + (varsa) final video + project.json oluşturur.

    has_video=True iken project'e final_video_path otomatik enjekte edilir
    (gerçek dosya diskte var olmalı, aksi halde _scan_history_projects
    projeyi atlar). Video olmadan "tamamlanmamış" durumunu test etmek için
    has_video=False bırakılıp project'e kendi final_video_path'i verilebilir.
    """
    task_path = tasks_root / task_id
    task_path.mkdir(parents=True)

    if has_video:
        video_path = task_path / "final.mp4"
        video_path.write_bytes(b"fake-mp4-bytes")
        if project is not None:
            project = {**project, "final_video_path": str(video_path)}

    if project is not None:
        (task_path / "project.json").write_text(json.dumps(project), encoding="utf-8")

    if mtime is not None:
        os.utime(task_path, (mtime, mtime))

    return task_path


def test_safe_load_project_snapshot_missing_file_returns_empty(tmp_path):
    helpers = _load_history_scan_helpers(tmp_path)
    assert helpers["_safe_load_project_snapshot"](str(tmp_path / "nope")) == {}


def test_safe_load_project_snapshot_corrupt_json_returns_empty(tmp_path):
    task_path = _make_task(tmp_path, "task-corrupt", project=None)
    (task_path / "project.json").write_text("{not valid json::", encoding="utf-8")

    helpers = _load_history_scan_helpers(tmp_path)
    assert helpers["_safe_load_project_snapshot"](str(task_path)) == {}


def test_scan_history_projects_empty_when_tasks_dir_missing(tmp_path):
    helpers = _load_history_scan_helpers(tmp_path / "does-not-exist")
    assert helpers["_scan_history_projects"]() == []


def test_scan_history_projects_empty_when_no_completed_tasks(tmp_path):
    helpers = _load_history_scan_helpers(tmp_path)
    assert helpers["_scan_history_projects"]() == []


def test_scan_history_projects_parses_valid_project(tmp_path):
    task_path = _make_task(
        tmp_path, "task-1", project={"topic": "The Roman Empire"}
    )

    helpers = _load_history_scan_helpers(tmp_path)
    results = helpers["_scan_history_projects"]()

    assert len(results) == 1
    assert results[0]["task_id"] == "task-1"
    assert results[0]["task_path"] == str(task_path)
    assert results[0]["project"]["topic"] == "The Roman Empire"
    assert results[0]["project"]["final_video_path"] == str(task_path / "final.mp4")


def test_scan_history_projects_skips_corrupt_project_json(tmp_path):
    """Bozuk project.json crash etmemeli, sadece galeriden sessizce atlanmalı."""
    task_path = _make_task(tmp_path, "task-corrupt", project=None, has_video=True)
    (task_path / "project.json").write_text("{not valid json::", encoding="utf-8")

    helpers = _load_history_scan_helpers(tmp_path)
    assert helpers["_scan_history_projects"]() == []


def test_scan_history_projects_skips_task_without_existing_video(tmp_path):
    """final_video_path diskte yoksa (ör. temizlenmiş/taşınmış) proje atlanır."""
    task_path = tmp_path / "task-no-video"
    task_path.mkdir()
    missing_video = task_path / "final.mp4"  # kasıtlı olarak hiç oluşturulmadı
    project = {"topic": "x", "final_video_path": str(missing_video)}
    (task_path / "project.json").write_text(json.dumps(project), encoding="utf-8")

    helpers = _load_history_scan_helpers(tmp_path)
    assert helpers["_scan_history_projects"]() == []


def test_scan_history_projects_skips_task_without_project_json(tmp_path):
    """project.json hiç yoksa (görev başka bir nedenle yarım kalmışsa) atlanır."""
    _make_task(tmp_path, "task-no-json", project=None, has_video=True)

    helpers = _load_history_scan_helpers(tmp_path)
    assert helpers["_scan_history_projects"]() == []


def test_scan_history_projects_respects_custom_limit_and_orders_newest_first(tmp_path):
    now = time.time()
    for i in range(5):
        _make_task(tmp_path, f"task-{i}", project={"topic": f"topic-{i}"}, mtime=now + i)

    helpers = _load_history_scan_helpers(tmp_path)
    results = helpers["_scan_history_projects"](limit=2)

    assert [r["task_id"] for r in results] == ["task-4", "task-3"]


def test_scan_history_projects_default_limit_is_thirty(tmp_path):
    helpers = _load_history_scan_helpers(tmp_path)
    assert helpers["_HISTORY_PROJECTS_LIMIT"] == 30

    now = time.time()
    for i in range(35):
        _make_task(
            tmp_path, f"task-{i:02d}", project={"topic": f"topic-{i}"}, mtime=now + i
        )

    results = helpers["_scan_history_projects"]()

    assert len(results) == 30
    assert results[0]["task_id"] == "task-34"


# -----------------------------------------------------------------------------
# _render_project_media_panel: Documentary Studio ve Geçmiş Üretimler'in ikisi
# de aynı fonksiyonu çağırıyor (Faz 4 DRY refactor). AppTest ile her iki
# sayfayı da gerçekten çalıştırıp aynı proje verisi için aynı panel
# çıktısını ürettiklerini doğruluyoruz -- ileride biri panel'i kendi içine
# kopyalayıp DRY'ı bozarsa bu testler ayrışmayı yakalar.
# -----------------------------------------------------------------------------


def _build_sample_project(base_dir: Path) -> dict:
    video_path = base_dir / "final.mp4"
    video_path.write_bytes(b"fake-mp4-bytes-for-test")
    thumbnail_path = base_dir / "thumb.jpg"
    # st.image() decodes the file via PIL to detect its format, so this needs
    # to be a real (if tiny) image -- unlike st.video(), which just streams
    # the raw bytes through without validating them.
    Image.new("RGB", (4, 4), color=(120, 60, 200)).save(thumbnail_path, format="JPEG")

    return {
        "topic": "The Roman Empire",
        "final_video_path": str(video_path),
        "thumbnail_path": str(thumbnail_path),
        "thumbnail_variant_b_path": "",
        "research_plan": {"grounded": True},
        "seo": {
            "title": "The Rise and Fall of Rome",
            "description": "A short documentary about ancient Rome.",
            "hashtags": ["rome", "history"],
            "chapters": ["00:00 Intro"],
            "end_screen_suggestion": "Subscribe for more.",
            "pinned_comment": "What do you think caused the fall?",
        },
        "quality_verdict": {
            "passed": True,
            "overall_score": 4.5,
            "coherence_score": 5,
            "pacing_fit_score": 4,
            "seo_quality_score": 4,
            "issues": ["Minor pacing dip in act two"],
        },
    }


def _assert_shared_panel_rendered(app, project):
    assert not app.exception

    assert len(app.get("video")) == 1
    # Geçmiş Üretimler'de kart zaten kendi thumbnail'ını gösteriyor
    # (_render_history_card), kart genişletildiğinde paylaşılan panel aynı
    # thumbnail'ı bir kez daha çiziyor -- bu yüzden sayı sayfaya göre 1 ya da
    # 2 olabilir, panelin kendisi en az bir görsel üretmiş olmalı.
    assert len(app.image) >= 1

    seo = project["seo"]
    title_input = next(
        w for w in app.text_input if w.label == EN_TRANSLATION["Documentary SEO Title"]
    )
    assert title_input.value == seo["title"]

    description_area = next(
        w
        for w in app.text_area
        if w.label == EN_TRANSLATION["Documentary SEO Description"]
    )
    assert description_area.value == seo["description"]

    hashtags_input = next(
        w
        for w in app.text_input
        if w.label == EN_TRANSLATION["Documentary SEO Hashtags"]
    )
    assert hashtags_input.value == " ".join(seo["hashtags"])

    quality = project["quality_verdict"]
    quality_note = next(
        m for m in app.markdown if EN_TRANSLATION["Documentary Quality Note"] in m.value
    )
    assert str(quality["overall_score"]) in quality_note.value

    assert any(
        EN_TRANSLATION["Documentary Research Grounded"] in c.value for c in app.caption
    )


def test_documentary_studio_page_renders_shared_media_panel(tmp_path):
    project = _build_sample_project(tmp_path)

    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_last_project"] = project
    app.run()

    _assert_shared_panel_rendered(app, project)


def test_history_page_renders_shared_media_panel_matching_studio(tmp_path):
    task_id = "task-1"
    task_path = tmp_path / task_id
    task_path.mkdir()
    project = _build_sample_project(task_path)
    (task_path / "project.json").write_text(json.dumps(project), encoding="utf-8")

    with patch.object(utils, "task_dir", return_value=str(tmp_path)):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app._page_hash = _HISTORY_PAGE_HASH
        app.session_state["ui_language"] = "en"
        app.session_state["history_expanded_task_id"] = task_id
        app.run()

    _assert_shared_panel_rendered(app, project)


def test_history_page_wiring_renders_without_error_when_empty(tmp_path):
    """Faz 2'nin Klasik Mod için yaptığı gibi (_LEGACY_PAGE_HASH ile
    doğrudan hedefleme) -- burada Geçmiş Üretimler ("history") sayfasının
    hatasız render edildiğini, hiç tamamlanmış proje yokken de doğru boş
    durumu gösterdiğini doğruluyor.
    """
    with patch.object(utils, "task_dir", return_value=str(tmp_path)):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app._page_hash = _HISTORY_PAGE_HASH
        app.session_state["ui_language"] = "en"
        app.run()

    assert not app.exception
    assert any(
        EN_TRANSLATION["Documentary History Empty"] in i.value for i in app.info
    )
