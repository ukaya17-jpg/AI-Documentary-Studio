import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"

# GÖREV 2 (TAM OTONOMİ): uzun-form video (10+ dakika) + 16:9 en/boy oranı.
# Aynı AppTest kısıtı burada da geçerli (format_func'lar tr() çağırıyor) --
# her senaryo tek bir .run() çağrısıyla, session_state önceden set edilerek
# doğrulanıyor.


def _button_by_key(app, key):
    return next(b for b in app.button if str(getattr(b, "key", "")).startswith(key))


def test_default_aspect_ratio_is_vertical():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.run()

    assert not app.exception
    combos = app.selectbox
    aspect_box = next(s for s in combos if s.key == "documentary_video_aspect")
    assert aspect_box.value == "9:16"


def test_can_select_landscape_aspect_ratio():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["documentary_video_aspect"] = "16:9"
    app.run()

    assert not app.exception
    combos = app.selectbox
    aspect_box = next(s for s in combos if s.key == "documentary_video_aspect")
    assert aspect_box.value == "16:9"


def test_extended_pacing_is_selectable_and_available_in_the_dropdown():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["documentary_pacing"] = "extended"
    app.run()

    assert not app.exception
    combos = app.selectbox
    pacing_box = next(s for s in combos if s.key == "documentary_pacing")
    # .options is the format_func's TRANSLATED display text, not the raw
    # enum value -- .value round-tripping to "extended" is what actually
    # matters (that's what flows into run_pipeline() unchanged).
    assert pacing_box.value == "extended"
    assert len(pacing_box.options) == 3


@patch("webui.Main.fal_video_service.is_configured", return_value=True)
def test_extended_pacing_with_ai_video_shows_repeated_frame_warning(_mock_configured):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["documentary_pacing"] = "extended"
    app.session_state["documentary_video_source"] = "ai_generated"
    app.run()

    assert not app.exception
    # extended: 20 sahne x 10s billed (30s sahne süresi Kling'in azami "10"
    # tier'ına yuvarlanıyor) x $0.045/s = $9.00
    assert any("9.00" in w.value for w in app.info)
    assert len(app.warning) == 1

    generate_button = _button_by_key(app, "documentary_generate_button")
    assert generate_button.disabled  # checkbox henüz onaylanmadı


@patch("webui.Main.fal_video_service.is_configured", return_value=True)
def test_short_pacing_with_ai_video_shows_no_extended_warning(_mock_configured):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["documentary_video_source"] = "ai_generated"
    app.run()

    assert not app.exception
    assert len(app.warning) == 0
