import json
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import Format, Pacing, Tone, TopicCategory

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

# GÖREV 1: Kategori/Ton/Format/Pacing seçenekleri artık `tr(f"Category: {value}")`
# gibi dinamik anahtarlarla çevriliyor. test_webui_i18n.py'deki AST tabanlı
# _TrKeyVisitor sadece literal string tr() çağrılarını yakalıyor (f-string'ler
# ast.JoinedStr, ast.Constant değil) -- bu yüzden bu yeni anahtarların i18n
# kapsamı ayrı, doğrudan bir testle doğrulanıyor, genel AST taramasına
# güvenilmiyor.
ALL_LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")


def _translation(locale):
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def _assert_labels_present(prefix, values):
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for value in values:
            key = f"{prefix}: {value}"
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def test_category_labels_present_and_non_empty_in_every_locale():
    _assert_labels_present("Category", ["auto"] + [c.value for c in TopicCategory])


def test_tone_labels_present_and_non_empty_in_every_locale():
    _assert_labels_present("Tone", ["auto"] + [t.value for t in Tone])


def test_format_labels_present_and_non_empty_in_every_locale():
    _assert_labels_present("Format", ["standard"] + [f.value for f in Format])


def test_pacing_labels_present_and_non_empty_in_every_locale():
    _assert_labels_present("Pacing", [p.value for p in Pacing])


def _selectbox_by_key(app, key):
    return next(w for w in app.selectbox if w.key == key)


def test_selectboxes_show_translated_labels_but_keep_raw_backend_value():
    """format_func sadece görünümü değiştirmeli -- selectbox'ın gerçek
    .value'su (run_pipeline()'a gidecek olan) hâlâ ham enum string'i olmalı,
    kullanıcının gördüğü metin ise session dilinde çevrilmiş olmalı.
    """
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "tr"
    app.run()

    category_select = _selectbox_by_key(app, "documentary_topic_category")
    assert category_select.value == "auto"
    assert "Tarih" in category_select.options
    assert "history" not in category_select.options

    tone_select = _selectbox_by_key(app, "documentary_tone")
    assert tone_select.value == "auto"
    assert "Bilimsel" in tone_select.options
    assert "scientific" not in tone_select.options

    format_select = _selectbox_by_key(app, "documentary_format")
    assert format_select.value == "standard"
    assert "Eğitici" in format_select.options
    assert "educational" not in format_select.options

    pacing_select = _selectbox_by_key(app, "documentary_pacing")
    assert pacing_select.value == "short"
    assert "Kısa" in pacing_select.options
    assert "long" not in pacing_select.options


def test_selectboxes_show_english_labels_for_english_session():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    category_select = _selectbox_by_key(app, "documentary_topic_category")
    assert "Healthy Living" in category_select.options
    assert "healthy_living" not in category_select.options


def test_preselected_non_default_value_stays_raw_regardless_of_ui_language():
    """Regresyon: session_state'te (ör. görev geri yükleme akışından) ham bir
    enum değeri önceden set edilmişse, format_func bunu Türkçe arayüzde bile
    bozmamalı -- selectbox'ın gerçek .value'su (run_pipeline()'a gidecek olan)
    hâlâ "healthy_living" olmalı, sadece gösterilen etiket çevrilmeli.

    (.select(raw_value).run() ile canlı bir kullanıcı tıklamasını simüle etmek
    yerine bunu tercih ediyoruz: AppTest'in kendi iç mekanizması, session_state
    okuyan bir format_func'ı pending-interaction serileştirmesi sırasında
    çağırdığında session_state henüz bağlı değil -- bu Streamlit'in test
    harness'ının bilinen bir sınırı, uygulama kodunda bir hata değil.)
    """
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "tr"
    app.session_state["documentary_topic_category"] = "healthy_living"
    app.run()

    category_select = _selectbox_by_key(app, "documentary_topic_category")
    assert category_select.value == "healthy_living"
    assert "Sağlıklı Yaşam" in category_select.options
