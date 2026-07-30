import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from streamlit.util import calc_hash

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"

# AI-üretimi video kaynağı (fal.ai/Kling, opt-in). 3-sayfa restructuring'den
# (kullanıcı onaylı, TAM OTONOMİ) sonra bu davranış "Belgesel Niteliği"
# sayfasına sabit (url_path="quality") -- artık bir selectbox ile açılmıyor,
# bu yüzden AI senaryoları o sayfaya `_page_hash` ile doğrudan navigasyonla
# ulaşıyor. "Stok Üretimler" varsayılan sayfa kaldığı için hash gerekmiyor.
#
# GÖREV 1'den öğrenilen AppTest kısıtı burada da geçerli: Video Source
# selectbox'ının format_func'ı tr() çağırıyor (dolaylı olarak session_state
# okuyor) -- bu yüzden her senaryo TEK bir .run() çağrısıyla, session_state
# önceden set edilerek doğrulanıyor, .select()/.click() zinciri kullanılmıyor.

_QUALITY_PAGE_HASH = calc_hash("quality")


def _button_by_key(app, key):
    return next(b for b in app.button if str(getattr(b, "key", "")).startswith(key))


def test_default_page_is_stock_and_ai_ui_is_hidden():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.run()

    assert not app.exception
    generate_button = _button_by_key(app, "documentary_generate_button")
    assert not generate_button.disabled
    assert not any("fal.ai" in w.value for w in app.warning)


@patch("webui.Main.fal_video_service.is_configured", return_value=False)
def test_ai_generated_without_fal_configured_shows_warning_and_disables_button(_mock_configured):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app._page_hash = _QUALITY_PAGE_HASH
    app.run()

    assert not app.exception
    generate_button = _button_by_key(app, "documentary_generate_button")
    assert generate_button.disabled
    assert len(app.warning) == 1


@patch("webui.Main.fal_video_service.is_configured", return_value=True)
def test_ai_generated_with_fal_configured_shows_cost_estimate_and_requires_confirmation(
    _mock_configured,
):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app._page_hash = _QUALITY_PAGE_HASH
    app.session_state["documentary_pacing"] = "short"
    app.run()

    assert not app.exception
    # short pacing: scene_count raised 4->7 (content-dropping fix, see
    # PROGRESS.md "Video-anlatım uyumsuzluğu") -- 7 scenes x 5s billed x
    # $0.045/s = $1.575, which the f"{...:.2f}" formatting renders as
    # "1.57" (float representation, not a rounding bug).
    assert any("1.57" in w.value for w in app.info)
    generate_button = _button_by_key(app, "documentary_generate_button")
    assert generate_button.disabled  # checkbox not confirmed yet
    assert not any("fal.ai" in w.value for w in app.warning)


@patch("webui.Main.fal_video_service.is_configured", return_value=True)
def test_confirming_ai_video_cost_enables_generate_button(_mock_configured):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app._page_hash = _QUALITY_PAGE_HASH
    app.session_state["documentary_ai_video_cost_confirmed"] = True
    app.run()

    assert not app.exception
    generate_button = _button_by_key(app, "documentary_generate_button")
    assert not generate_button.disabled


@patch("webui.Main.fal_video_service.is_configured", return_value=True)
def test_long_pacing_rounds_billed_duration_up_to_ten_seconds(_mock_configured):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app._page_hash = _QUALITY_PAGE_HASH
    app.session_state["documentary_pacing"] = "long"
    app.run()

    assert not app.exception
    # long pacing: 7 scenes x 10s billed (8s scene rounds UP to Kling's "10"
    # tier, not "5") x $0.045/s = $3.15
    assert any("3.15" in w.value for w in app.info)


@patch("webui.Main.fal_video_service.is_configured", return_value=True)
def test_ai_video_provider_selector_defaults_to_kling(_mock_configured):
    # GÖREV 3 (gece oturumu): Kling/Veo seçici -- Hailuo BİLİNÇLİ OLARAK
    # burada yok (9:16 desteklemiyor, ADIM 3'ten beri webui'den gizli).
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app._page_hash = _QUALITY_PAGE_HASH
    app.run()

    assert not app.exception
    provider_select = next(
        s for s in app.selectbox if str(getattr(s, "key", "")) == "documentary_ai_video_provider"
    )
    assert provider_select.value == "kling"
    # .options exposes the format_func-rendered display labels, not the raw
    # underlying values.
    assert list(provider_select.options) == ["Kling", "Veo"]


@patch("webui.Main.fal_video_service.is_configured", return_value=True)
def test_selecting_veo_updates_cost_estimate(_mock_configured):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app._page_hash = _QUALITY_PAGE_HASH
    app.session_state["documentary_pacing"] = "short"
    app.session_state["documentary_ai_video_provider"] = "veo"
    app.run()

    assert not app.exception
    # short pacing: 7 scenes x 6s billed (5s scene rounds UP to Veo's "6s",
    # nearest of "4s"/"6s"/"8s") x $0.10/s = $4.20
    assert any("4.20" in w.value for w in app.info)


if __name__ == "__main__":
    import unittest

    unittest.main()
