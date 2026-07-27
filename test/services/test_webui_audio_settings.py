import json
import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.documentary_project import DocumentaryProject
from app.models.research_plan import ResearchPlan
from app.pipeline import default_pipeline

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

ALL_LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")

# GÖREV D (kullanıcı onaylı): Klasik Mod'daki ses hızı/seviyesi + BGM
# ayarlarını Documentary Studio'ya geri getiriyor -- şimdiye kadar sadece
# ses adı (voice_name) vardı. Sonilo/ElevenLabs BGM üretimi bilinçli olarak
# kapsam dışı (sadece eski task.py'de yaşıyor, default_pipeline.py'ye hiç
# bağlanmamış) -- burada sadece Yok/Rastgele/Kendi Dosyanı Yükle var.
NEW_KEYS = ("Documentary Audio Settings",)


def _translation(locale):
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def test_audio_settings_keys_present_and_non_empty_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in NEW_KEYS:
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def _widget_by_key(widgets, key):
    return next(w for w in widgets if str(getattr(w, "key", "")) == key)


def test_default_voice_and_bgm_values():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    assert not app.exception
    voice_volume = _widget_by_key(app.selectbox, "documentary_voice_volume")
    voice_rate = _widget_by_key(app.selectbox, "documentary_voice_rate")
    bgm_type = _widget_by_key(app.selectbox, "documentary_bgm_type")
    bgm_volume = _widget_by_key(app.selectbox, "documentary_bgm_volume")

    assert voice_volume.value == 1.0
    assert voice_rate.value == 1.0
    assert bgm_type.value == "random"
    assert bgm_volume.value == 0.2
    assert not bgm_volume.disabled


def test_bgm_volume_disabled_when_source_is_none():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_bgm_type"] = ""
    app.run()

    assert not app.exception
    bgm_volume = _widget_by_key(app.selectbox, "documentary_bgm_volume")
    assert bgm_volume.disabled


def test_custom_bgm_shows_uploader_only_when_selected():
    app_without = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app_without.session_state["ui_language"] = "en"
    app_without.session_state["documentary_bgm_type"] = "random"
    app_without.run()

    assert not app_without.exception
    assert not any(
        str(getattr(w, "key", "")) == "documentary_custom_bgm_uploader"
        for w in app_without.file_uploader
    )

    app_with = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app_with.session_state["ui_language"] = "en"
    app_with.session_state["documentary_bgm_type"] = "custom"
    app_with.run()

    assert not app_with.exception
    assert any(
        str(getattr(w, "key", "")) == "documentary_custom_bgm_uploader"
        for w in app_with.file_uploader
    )


def _fake_project():
    project = DocumentaryProject(
        project_id="fake-id",
        topic="Test Topic",
        research_plan=ResearchPlan(topic="Test Topic"),
    )
    project.final_video_path = ""
    return project


def test_generate_passes_voice_and_bgm_settings_to_run_pipeline():
    """Yeni widget'ların döndürdüğü değerler run_pipeline()'a doğru
    kwarg'larla ulaşıyor mu -- tek .run() (GÖREV 1'den beri bilinen
    format_func/session_state kısıtı yüzünden bu sayfada ikinci bir .run()
    Pacing selectbox'ını kırıyor, bu yüzden her şey ilk run'dan önce
    session_state'e önceden yazılıyor).
    """
    with patch.object(
        default_pipeline, "run_pipeline", return_value=_fake_project()
    ) as run_mock:
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_voice_volume"] = 1.5
        app.session_state["documentary_voice_rate"] = 1.3
        app.session_state["documentary_bgm_type"] = "random"
        app.session_state["documentary_bgm_volume"] = 0.4
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_called_once()
    kwargs = run_mock.call_args.kwargs
    assert kwargs["voice_rate"] == 1.3
    assert kwargs["voice_volume"] == 1.5
    assert kwargs["bgm_type"] == "random"
    assert kwargs["bgm_volume"] == 0.4
    assert kwargs["bgm_file"] == ""


def test_generate_with_no_bgm_passes_empty_bgm_type():
    with patch.object(
        default_pipeline, "run_pipeline", return_value=_fake_project()
    ) as run_mock:
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_bgm_type"] = ""
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_called_once()
    kwargs = run_mock.call_args.kwargs
    assert kwargs["bgm_type"] == ""
    assert kwargs["bgm_file"] == ""
