import json
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

# GÖREV 2 (SEO Engine genişletmesi, OTONOM KARAR): title_variants/keywords
# webui'de nasıl gösteriliyor -- ADIM 0 kuralı gereği (her yeni alanın
# gerçek bir tüketicisi olsun) bu testler tam da o tüketiciyi doğruluyor.
ALL_LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")

NEW_SEO_KEYS = (
    "Documentary SEO Title Variants",
    "Documentary SEO Title Variants Help",
    "Documentary SEO Keywords",
    "Documentary SEO Keywords Help",
)


def _translation(locale):
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def test_seo_extension_keys_present_and_non_empty_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in NEW_SEO_KEYS:
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def _sample_project_with_seo_extras(base_dir: Path) -> dict:
    video_path = base_dir / "final.mp4"
    video_path.write_bytes(b"fake-mp4-bytes-for-test")
    return {
        "topic": "The Fall of Rome",
        "final_video_path": str(video_path),
        "thumbnail_path": "",
        "thumbnail_variant_b_path": "",
        "research_plan": {"grounded": True},
        "seo": {
            "title": "The Fall of Rome",
            "description": "How the mightiest empire in history collapsed.",
            "hashtags": ["rome", "history"],
            "title_variants": ["Why Rome Really Fell", "The Empire's Final Days"],
            "keywords": ["roman empire", "fall of rome", "ancient history"],
        },
    }


def test_title_variants_render_with_translated_label_right_after_the_title(tmp_path):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_last_project"] = _sample_project_with_seo_extras(tmp_path)
    app.run()

    assert not app.exception

    en = _translation("en")
    title_variants_widget = next(
        w for w in app.text_area if w.label == en["Documentary SEO Title Variants"]
    )
    assert title_variants_widget.value == "Why Rome Really Fell\nThe Empire's Final Days"


def test_keywords_render_inside_seo_extras_expander_comma_joined(tmp_path):
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_last_project"] = _sample_project_with_seo_extras(tmp_path)
    app.run()

    assert not app.exception

    en = _translation("en")
    keywords_widget = next(
        w for w in app.text_input if w.label == en["Documentary SEO Keywords"]
    )
    assert keywords_widget.value == "roman empire, fall of rome, ancient history"

    # hashtags kalıyor, keywords'ten bağımsız -- ikisi de aynı anda görünmeli.
    hashtags_widget = next(
        w for w in app.text_input if w.label == en["Documentary SEO Hashtags"]
    )
    assert hashtags_widget.value == "rome history"


def test_missing_title_variants_and_keywords_render_nothing_extra(tmp_path):
    """Regresyon: eski/daha önce üretilmiş bir project.json'da bu iki alan
    hiç yoksa (GÖREV 2'den önce üretilmiş gerçek bir belgesel), yeni
    widget'lar sessizce hiç render edilmemeli -- crash yok, boş widget yok.
    """
    project = _sample_project_with_seo_extras(tmp_path)
    del project["seo"]["title_variants"]
    del project["seo"]["keywords"]

    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_last_project"] = project
    app.run()

    assert not app.exception

    en = _translation("en")
    assert not any(
        w.label == en["Documentary SEO Title Variants"] for w in app.text_area
    )
    assert not any(w.label == en["Documentary SEO Keywords"] for w in app.text_input)
