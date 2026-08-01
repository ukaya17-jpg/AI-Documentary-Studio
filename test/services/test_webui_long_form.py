import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from streamlit.util import calc_hash

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"

# GÖREV 2 (TAM OTONOMİ): uzun-form video (10+ dakika) + 16:9 en/boy oranı.
# Aynı AppTest kısıtı burada da geçerli (format_func'lar tr() çağırıyor) --
# her senaryo tek bir .run() çağrısıyla, session_state önceden set edilerek
# doğrulanıyor.
#
# 3-sayfa restructuring (kullanıcı onaylı, TAM OTONOMİ): AI video senaryoları
# artık "Belgesel Niteliği" sayfasına (url_path="quality") sabit -- bir
# selectbox ile açılmıyor, page hash ile navigasyonla ulaşılıyor.
_QUALITY_PAGE_HASH = calc_hash("quality")


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
    app._page_hash = _QUALITY_PAGE_HASH
    app.session_state["documentary_pacing"] = "extended"
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
    app._page_hash = _QUALITY_PAGE_HASH
    app.run()

    assert not app.exception
    assert len(app.warning) == 0


def _aspect_value(app):
    return next(s for s in app.selectbox if s.key == "documentary_video_aspect").value


# GÖREV 1 (gece oturumu): kullanıcı "Uzun" (Pacing.long) ile "Belgesel
# Uzunluğunda (10+ dk)" (Pacing.extended) etiketlerini karıştırıp extended
# seçtiğinde video hâlâ dikey (9:16) çıkıyordu -- Aspect Ratio, Pacing'den
# TAMAMEN bağımsızdı (GÖREV 2'den beri hiç otomatik bağlanmamıştı, bu bir
# regresyon değildi). Artık short/long -> extended CANLI geçişinde Aspect
# Ratio otomatik 16:9'a geçiyor.
#
# `documentary_pacing_last_seen` ön-seed edilerek "kullanıcı bu oturumda
# zaten sayfadaydı" simüle ediliyor -- bu sayfada ikinci bir .run()
# format_func'lı selectbox'ları kırdığı için (bkz. yukarıdaki GÖREV 2
# yorumu), geçiş TEK bir .run() içinde, session_state'i geçiş ÖNCESİ
# duruma göre önceden yazarak test ediliyor.
def test_switching_to_extended_pacing_auto_selects_landscape_aspect():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["documentary_pacing_last_seen"] = "short"
    app.session_state["documentary_pacing"] = "extended"
    app.run()

    assert not app.exception
    assert _aspect_value(app) == "16:9"


def test_switching_to_long_pacing_does_not_change_aspect():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["documentary_pacing_last_seen"] = "short"
    app.session_state["documentary_pacing"] = "long"
    app.run()

    assert not app.exception
    assert _aspect_value(app) == "9:16"


def test_fresh_session_with_extended_prepopulated_does_not_force_aspect_change():
    # Taze bir oturumda (ör. bir görev geri yüklemesi) pacing zaten
    # "extended" olarak gelmiş olabilir -- documentary_pacing_last_seen
    # hiç set edilmemiş (canlı bir geçiş YOK), aspect ratio'ya
    # dokunulmamalı.
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["documentary_pacing"] = "extended"
    app.run()

    assert not app.exception
    assert _aspect_value(app) == "9:16"


def test_user_can_override_back_to_vertical_after_auto_switch():
    # pacing zaten extended'te KALIYOR (geçiş yok) -- kullanıcının elle
    # 9:16'ya geri döndürdüğü değer TEKRAR ezilmemeli.
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["documentary_pacing_last_seen"] = "extended"
    app.session_state["documentary_pacing"] = "extended"
    app.session_state["documentary_video_aspect"] = "9:16"
    app.run()

    assert not app.exception
    assert _aspect_value(app) == "9:16"
