import json
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

ALL_LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")

# GÖREV E (kullanıcı onaylı): 15 kart hep açık sayfayı çok uzatıyordu -- artık
# ikisi de kapalı başlayan bir st.expander içinde, başlık her zaman güncel
# seçimi özetliyor. GÖREV 1'den bilinen kısıt burada da geçerli: bu sayfada
# HERHANGİ bir ikinci .run() (bir tıklamayı takiben de olsa) format_func'lı
# selectbox'ları kırıyor -- bu yüzden her test tek bir .run() ile,
# session_state önceden set edilerek doğrulanıyor.
NEW_KEYS = ("Documentary Topic Category Select", "Documentary Tone Select")


def _translation(locale):
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def test_expander_title_keys_present_and_non_empty_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in NEW_KEYS:
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def _expander_starting_with(app, prefix):
    return next(e for e in app.expander if e.label.startswith(prefix))


def test_category_and_tone_expanders_default_to_auto_summary():
    en = _translation("en")
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    assert not app.exception
    category_expander = _expander_starting_with(
        app, en["Documentary Topic Category Select"]
    )
    tone_expander = _expander_starting_with(app, en["Documentary Tone Select"])
    assert category_expander.label.endswith(en["Category: auto"])
    assert tone_expander.label.endswith(en["Tone: auto"])


def test_expander_titles_reflect_a_preselected_category_and_tone():
    en = _translation("en")
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_topic_category"] = "history"
    app.session_state["documentary_tone"] = "credibility"
    app.run()

    assert not app.exception
    category_expander = _expander_starting_with(
        app, en["Documentary Topic Category Select"]
    )
    tone_expander = _expander_starting_with(app, en["Documentary Tone Select"])
    assert category_expander.label.endswith(en["Category: history"])
    assert tone_expander.label.endswith(en["Tone: credibility"])


def test_cards_still_reachable_inside_collapsed_expanders():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    assert not app.exception
    assert any(
        str(getattr(b, "key", "")) == "category_btn_history" for b in app.button
    )
    assert any(str(getattr(b, "key", "")) == "tone_btn_credibility" for b in app.button)
