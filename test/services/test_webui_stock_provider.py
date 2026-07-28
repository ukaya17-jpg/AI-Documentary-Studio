import json
import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from streamlit.util import calc_hash

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.models.documentary_project import DocumentaryProject
from app.models.research_plan import ResearchPlan
from app.pipeline import default_pipeline

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

ALL_LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")

# ADIM 1 (Provider Sistemi keşif raporu, kullanıcı onaylı): material.
# download_videos() zaten pexels/pixabay/coverr'ı tam destekliyordu (Klasik
# Mod'un yıllardır kullandığı kod) -- Documentary Studio'nun webui'si hiç
# seçenek sunmuyordu, her zaman "pexels"e sabitti. GÖREV 1'den bilinen
# kısıt burada da geçerli: bu sayfada ikinci bir .run() format_func'lı
# selectbox'ları kırıyor, bu yüzden her test tek bir .run() ile,
# session_state önceden set edilerek doğrulanıyor.
NEW_KEYS = (
    "Documentary Stock Provider",
    "Documentary Stock Provider: pexels",
    "Documentary Stock Provider: pixabay",
    "Documentary Stock Provider: coverr",
)

# 3-sayfa restructuring (kullanıcı onaylı, TAM OTONOMİ): Video Kaynağı artık
# bir selectbox değil, "Belgesel Niteliği" sayfasına (url_path="quality")
# sabit -- AI senaryosuna page hash ile navigasyonla ulaşılıyor.
_QUALITY_PAGE_HASH = calc_hash("quality")


def _translation(locale):
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def _widget_by_key(widgets, key):
    return next(w for w in widgets if str(getattr(w, "key", "")) == key)


def test_stock_provider_keys_present_and_non_empty_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in NEW_KEYS:
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def test_stock_provider_selector_shown_by_default_with_pexels_selected():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    assert not app.exception
    stock_provider = _widget_by_key(app.selectbox, "documentary_stock_provider")
    assert stock_provider.value == "pexels"


def test_stock_provider_selector_hidden_on_documentary_quality_page():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app._page_hash = _QUALITY_PAGE_HASH
    app.session_state["ui_language"] = "en"
    app.run()

    assert not app.exception
    assert not any(
        str(getattr(w, "key", "")) == "documentary_stock_provider"
        for w in app.selectbox
    )


def _fake_project():
    project = DocumentaryProject(
        project_id="fake-id",
        topic="Test Topic",
        research_plan=ResearchPlan(topic="Test Topic"),
    )
    project.final_video_path = ""
    return project


def test_generate_passes_selected_stock_provider_to_run_pipeline():
    # UYARI (gerçek bir prod olayından öğrenildi): _render_documentary_
    # advanced_settings() HER sayfa render'ında config.save_config()
    # çağırıyor (GÖREV G) -- config.app'i mock'lu bir test değeriyle
    # patch'leyip save_config()'i MOCK'LAMAZSAK, bu test'in sahte değeri
    # gerçek config.toml'a yazılır (bir kez tam olarak bu yüzden production
    # pexels_api_keys'i "test-pexels-key" ile ezilmişti). Her ikisi de
    # HER ZAMAN birlikte patch'lenmeli.
    test_config = dict(config.app, pixabay_api_keys="test-pixabay-key")
    with (
        patch.object(config, "app", test_config),
        patch.object(config, "save_config"),
        patch.object(
            default_pipeline, "run_pipeline", return_value=_fake_project()
        ) as run_mock,
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_stock_provider"] = "pixabay"
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_called_once()
    assert run_mock.call_args.kwargs["video_source"] == "pixabay"


def test_generate_blocked_with_clear_error_when_provider_api_key_missing():
    test_config = dict(config.app)
    test_config.pop("coverr_api_keys", None)
    en = _translation("en")

    with (
        patch.object(config, "app", test_config),
        patch.object(config, "save_config"),
        patch.object(default_pipeline, "run_pipeline") as run_mock,
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_stock_provider"] = "coverr"
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_not_called()
    assert any(
        item.value == en["Please Enter the Coverr API Key"] for item in app.error
    )


def test_generate_with_default_pexels_provider_still_works_without_new_keys():
    """Regresyon kilidi: yeni sağlayıcı seçici eklenmeden ÖNCEKİ davranış
    (varsayılan pexels, gerçek pexels key varsa üretim engellenmez) hâlâ
    aynen çalışıyor."""
    test_config = dict(config.app, pexels_api_keys="test-pexels-key")
    with (
        patch.object(config, "app", test_config),
        patch.object(config, "save_config"),
        patch.object(
            default_pipeline, "run_pipeline", return_value=_fake_project()
        ) as run_mock,
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_called_once()
    assert run_mock.call_args.kwargs["video_source"] == "pexels"
