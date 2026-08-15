import json
import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from streamlit.util import calc_hash

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.departments.creative import script_generator
from app.models.documentary_project import DocumentaryProject
from app.models.research_plan import ResearchPlan
from app.pipeline import default_pipeline

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"
_QUALITY_PAGE_HASH = calc_hash("quality")

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

# "Stok Arama Kelimesi İpucu" planı (kullanıcı onaylı): AYNI expander,
# SADECE Stok Üretimler sayfasında (varsayılan sayfa, page hash yok) görünür
# -- bkz. test_webui_stock_provider.py'nin AYNI "quality" page hash deseni.
STOCK_KEYWORD_HINT_KEYS = (
    "Documentary Stock Keyword Hint",
    "Documentary Stock Keyword Hint Help",
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


def test_stock_keyword_hint_keys_present_and_non_empty_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in STOCK_KEYWORD_HINT_KEYS:
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def test_stock_keyword_hint_field_shown_on_stock_productions_page():
    # Default page (no page hash override) is "Stok Üretimler" (stock).
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    assert not app.exception
    hint = _widget_by_key(app.text_area, "documentary_stock_keyword_hint")
    assert hint.value == ""


def test_stock_keyword_hint_field_hidden_on_documentary_quality_page():
    # AI-generated video page: a stock-footage search hint is meaningless
    # there, so the field must not render at all.
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app._page_hash = _QUALITY_PAGE_HASH
    app.run()

    assert not app.exception
    assert not any(
        str(getattr(w, "key", "")) == "documentary_stock_keyword_hint"
        for w in app.text_area
    )


def test_system_prompt_and_custom_requirements_default_to_stock_variant_on_stock_page():
    # GÖREV 5 (gece oturumu): alanlar artık boş başlamıyor -- varsayılan
    # sayfa "Stok Üretimler" olduğu için (bkz. PROGRESS.md) burada stok-
    # görsel-uyumlu varyant beklenir.
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    assert not app.exception
    system_prompt = _widget_by_key(app.text_area, "documentary_custom_system_prompt")
    custom_requirements = _widget_by_key(
        app.text_area, "documentary_custom_requirements"
    )
    from webui.Main import (
        _DOCUMENTARY_DEFAULT_CUSTOM_REQUIREMENTS,
        _DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_STOCK,
    )

    assert system_prompt.value == _DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_STOCK
    assert custom_requirements.value == _DOCUMENTARY_DEFAULT_CUSTOM_REQUIREMENTS
    assert script_generator.DEFAULT_SCRIPT_SYSTEM_PROMPT in system_prompt.proto.placeholder


def test_system_prompt_defaults_to_ai_video_variant_on_quality_page():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app._page_hash = _QUALITY_PAGE_HASH
    app.run()

    assert not app.exception
    system_prompt = _widget_by_key(app.text_area, "documentary_custom_system_prompt")
    from webui.Main import _DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_AI_VIDEO

    assert system_prompt.value == _DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_AI_VIDEO
    # İki varyant birbirinden farklı olmalı -- sayfaya göre gerçekten
    # değişiyor, aynı metin iki yere kopyalanmış değil.
    from webui.Main import _DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_STOCK

    assert _DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_AI_VIDEO != _DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_STOCK


def test_user_can_still_clear_the_default_to_empty():
    # Kullanıcı varsayılanı silip boş bırakabilmeli -- ön-doldurma bir
    # zorunluluk değil, sadece bir başlangıç noktası.
    with patch.object(
        default_pipeline, "run_pipeline", return_value=_fake_project()
    ) as run_mock:
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_custom_system_prompt"] = ""
        app.session_state["documentary_custom_requirements"] = ""
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_called_once()
    kwargs = run_mock.call_args.kwargs
    assert kwargs["custom_system_prompt"] == ""
    assert kwargs["custom_requirements"] == ""


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


def test_generate_passes_stock_keyword_hint_to_run_pipeline_on_stock_page():
    with patch.object(
        default_pipeline, "run_pipeline", return_value=_fake_project()
    ) as run_mock:
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_stock_keyword_hint"] = "Ottoman archives"
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_called_once()
    assert run_mock.call_args.kwargs["stock_keyword_hint"] == "Ottoman archives"


def test_generate_with_untouched_stock_keyword_hint_passes_empty_string():
    # Regression guard: unlike custom_system_prompt/custom_requirements (which
    # pre-fill with a default), the hint field has no default text -- leaving
    # it untouched must reach run_pipeline() as "", not some placeholder.
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
    assert run_mock.call_args.kwargs["stock_keyword_hint"] == ""


def test_generate_with_untouched_advanced_fields_passes_the_defaults():
    # GÖREV 5 (gece oturumu): alanlara artık dokunulmadan "Generate"
    # tıklanırsa, boş string değil, ön-dolu varsayılan metinler
    # run_pipeline()'a gidiyor -- bu, önceki "boş string gider" davranışının
    # kasıtlı değişimi (bkz. NEW test_user_can_still_clear_the_default_to_empty
    # for the still-supported empty-string path).
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
    from webui.Main import (
        _DOCUMENTARY_DEFAULT_CUSTOM_REQUIREMENTS,
        _DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_STOCK,
    )

    assert kwargs["custom_system_prompt"] == _DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_STOCK
    assert kwargs["custom_requirements"] == _DOCUMENTARY_DEFAULT_CUSTOM_REQUIREMENTS
