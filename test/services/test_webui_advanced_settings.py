import json
import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.departments.creative import script_generator
from app.models.documentary_project import DocumentaryProject
from app.models.research_plan import ResearchPlan
from app.pipeline import default_pipeline

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

ALL_LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")

# GÖREV F + G (kullanıcı onaylı): "Gelişmiş Ayarlar" expander'ında sistem
# promptu + özel senaryo gereksinimleri (F) ve altyazı font ailesi/boyut/
# rengi (G). Font/Font Size/Font Color anahtarları Klasik Mod'dan zaten
# vardı, sadece bu üçü (F'nin metinleri + expander başlığı) yeni.
NEW_KEYS = (
    "Documentary Advanced Settings",
    "Documentary System Prompt",
    "Documentary System Prompt Help",
    "Documentary Custom Requirements",
    "Documentary Custom Requirements Help",
)


def _translation(locale):
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def _widget_by_key(widgets, key):
    return next(w for w in widgets if str(getattr(w, "key", "")) == key)


def test_advanced_settings_keys_present_and_non_empty_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in NEW_KEYS:
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def test_system_prompt_and_custom_requirements_default_empty():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    assert not app.exception
    system_prompt = _widget_by_key(app.text_area, "documentary_custom_system_prompt")
    custom_requirements = _widget_by_key(
        app.text_area, "documentary_custom_requirements"
    )
    assert system_prompt.value == ""
    assert custom_requirements.value == ""
    assert script_generator.DEFAULT_SCRIPT_SYSTEM_PROMPT in system_prompt.proto.placeholder


def test_font_settings_default_to_configured_values():
    with patch.object(
        config,
        "ui",
        {"font_name": "MicrosoftYaHeiBold.ttc", "font_size": 75, "text_fore_color": "#FF0000"},
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.run()

    assert not app.exception
    font_select = _widget_by_key(app.selectbox, "documentary_font_name_select")
    font_size = _widget_by_key(app.slider, "documentary_font_size_slider")
    font_color = _widget_by_key(app.color_picker, "documentary_font_color_picker")
    assert font_select.value == "MicrosoftYaHeiBold.ttc"
    assert font_size.value == 75
    assert font_color.value == "#FF0000"


def test_font_settings_are_persisted_via_save_config():
    """Klasik Mod'un aksine Documentary Studio hiçbir yerde
    config.save_config() çağırmıyordu -- bu üç ayar RAM'de kalıp bir sonraki
    süreç yeniden başlatmasında sessizce eski değerlere dönerdi.
    """
    with patch.object(config, "save_config") as save_mock:
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.run()

    assert not app.exception
    save_mock.assert_called()


def _fake_project():
    project = DocumentaryProject(
        project_id="fake-id",
        topic="Test Topic",
        research_plan=ResearchPlan(topic="Test Topic"),
    )
    project.final_video_path = ""
    return project


def test_generate_passes_system_prompt_and_custom_requirements_to_run_pipeline():
    """GÖREV 1'den bilinen kısıt yüzünden (bu sayfada ikinci bir .run()
    format_func'lı selectbox'ları kırıyor) her şey tek bir .run()'dan önce
    session_state'e önceden yazılıyor.
    """
    with patch.object(
        default_pipeline, "run_pipeline", return_value=_fake_project()
    ) as run_mock:
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_custom_system_prompt"] = (
            "Write like a noir detective."
        )
        app.session_state["documentary_custom_requirements"] = (
            "Always mention exact dates."
        )
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_called_once()
    kwargs = run_mock.call_args.kwargs
    assert kwargs["custom_system_prompt"] == "Write like a noir detective."
    assert kwargs["custom_requirements"] == "Always mention exact dates."


def test_generate_with_blank_advanced_fields_passes_empty_strings():
    with patch.object(
        default_pipeline, "run_pipeline", return_value=_fake_project()
    ) as run_mock:
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_called_once()
    kwargs = run_mock.call_args.kwargs
    assert kwargs["custom_system_prompt"] == ""
    assert kwargs["custom_requirements"] == ""
