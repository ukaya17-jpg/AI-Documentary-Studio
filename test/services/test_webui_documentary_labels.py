import json
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import characters
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
#
# Modernizasyon C: bu dosyada kasıtlı olarak hiçbir .click().run() zinciri
# yok. Deneyerek bulundu -- Format/Pacing selectbox'larının format_func'ı
# (GÖREV 1) session_state okuyor; AppTest herhangi bir *ikinci* .run()
# çağrısında (bir tıklamayı takiben de olsa) TÜM widget ağacının durumunu
# yeniden serileştiriyor, bu da etkileşimle hiç ilgisi olmayan Format/Pacing
# selectbox'larının format_func'ını da tetikleyip aynı bağlanmamış-context
# quirk'üne (bkz. GÖREV 1 commit notu) düşürüyor. Üretimde bu hiç sorun
# değil (gerçek Streamlit session'ında context her zaman bağlı) -- sadece
# AppTest'in kendi test harness sınırı. Bu yüzden her test tek bir .run()
# çağrısıyla, session_state'i ÖNCEDEN set ederek doğrulanıyor.
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


def test_category_and_tone_auto_descriptions_present_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in (
            "Category Auto Description",
            "Tone Auto Description",
            "Tone Neutral Fallback Description",
        ):
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def test_tone_preview_keys_present_and_non_empty_in_every_locale():
    # Tone.neutral bilinçli olarak dışarıda: kendi PROFILE_PROMPTS girdisi
    # yok, ayrı ("Tone Neutral Fallback Description") bir key kullanıyor.
    tone_values = [t.value for t in Tone if t != Tone.neutral]
    _assert_labels_present("Tone Preview", tone_values)


def test_category_preview_keys_present_and_non_empty_in_every_locale():
    _assert_labels_present("Category Preview", [c.value for c in TopicCategory])


# "Çoklu Karakter Sistemi" planı (kullanıcı onaylı): Character kart grid'i
# de Category/Tone ile AYNI dinamik-key deseni (tr(f"Character: {value}")) --
# aynı gerekçeyle (AST taraması f-string'leri yakalamıyor) ayrı doğrulanıyor.
_ALL_CHARACTER_VALUES = (
    [characters.NO_CHARACTER] + list(characters._CHARACTER_SLUGS) + list(characters.CHARACTER_PAIRS)
)


def test_character_labels_present_and_non_empty_in_every_locale():
    _assert_labels_present("Character", _ALL_CHARACTER_VALUES)


def test_character_preview_keys_present_and_non_empty_in_every_locale():
    # "none" kasıtlı olarak dışarıda: kendi "Character None Description"
    # key'i var (Tone.neutral/Category "auto" ile aynı desen).
    _assert_labels_present(
        "Character Preview", [v for v in _ALL_CHARACTER_VALUES if v != characters.NO_CHARACTER]
    )


def test_character_none_description_present_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        assert "Character None Description" in translation
        assert translation["Character None Description"].strip()


def test_turkish_card_previews_are_not_leaked_english_llm_prompt_text():
    """Regresyon: kart önizlemesi PROFILE_PROMPTS'tan (LLM'e giden İngilizce
    prompt metni) DEĞİL, ayrı çevrilmiş "Tone/Category Preview: {value}"
    key'lerinden gelmeli -- Türkçe arayüzde bu İngilizce metnin birebir
    sızmadığını doğruluyor.
    """
    tr_translation = _translation("tr")
    preview_texts = [
        v for k, v in tr_translation.items()
        if k.startswith("Tone Preview:") or k.startswith("Category Preview:")
    ]
    assert preview_texts, "no preview keys found in tr.json"

    # PROFILE_PROMPTS'un İngilizce metinlerinde sürekli tekrar eden, gerçek
    # bir Türkçe cümlede hiç geçmeyecek kalıplar -- eskiden kaçan bug tam
    # olarak bu kalıpların Türkçe arayüzde görünmesiydi.
    english_llm_prompt_markers = ("Ground the narration", "Favor ", "documentary.")
    for text in preview_texts:
        for marker in english_llm_prompt_markers:
            assert marker not in text, f"English PROFILE_PROMPTS text leaked into tr.json: {text!r}"


def _selectbox_by_key(app, key):
    return next(w for w in app.selectbox if w.key == key)


def _button_by_key(app, key):
    return next(w for w in app.button if w.key == key)


def test_format_and_pacing_selectboxes_still_show_translated_labels():
    """Format ve Pacing kart grid'ine dönüşmedi (sadece Kategori/Ton
    dönüştü), hâlâ selectbox -- GÖREV 1'in regresyon garantisi (ham değer +
    çevrilmiş görünüm) burada da geçerliliğini koruyor.
    """
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "tr"
    app.run()

    format_select = _selectbox_by_key(app, "documentary_format")
    assert format_select.value == "standard"
    assert "Eğitici" in format_select.options
    assert "educational" not in format_select.options

    pacing_select = _selectbox_by_key(app, "documentary_pacing")
    assert pacing_select.value == "short"
    # "Pacing İsim Netleştirmesi" (kullanıcı onaylı): eski "Kısa"/"Uzun"
    # etiketleri ikisinin de aslında kısa (35sn/56sn) olduğunu, gerçek uzun
    # videonun "extended" olduğunu gizliyordu -- artık süre bilgisi
    # etikette (raw enum değeri "short" hâlâ değişmedi, sadece görünen
    # metin).
    assert "Hızlı Shorts (35sn)" in pacing_select.options
    assert "long" not in pacing_select.options


def test_category_and_tone_cards_show_translated_labels_and_previews():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "tr"
    app.run()

    healthy_living_button = _button_by_key(app, "category_btn_healthy_living")
    assert healthy_living_button.label == "🥗  Sağlıklı Yaşam"

    scientific_button = _button_by_key(app, "tone_btn_scientific")
    assert scientific_button.label == "🔬  Bilimsel"

    # Her kartın altında bir stil önizlemesi (st.caption) var, boş olmamalı.
    captions = [c.value for c in app.caption]
    assert any(cap.strip() for cap in captions)


def test_default_selection_is_auto_and_rendered_as_primary():
    """Regresyon: hiçbir session_state ön ayarı yokken (eski selectbox'ların
    index=0 varsayılanıyla aynı davranış), "auto" kartı hem kategori hem ton
    için seçili (primary buton) olarak render edilmeli, diğerleri secondary.
    """
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    assert _button_by_key(app, "category_btn_auto").proto.type == "primary"
    assert _button_by_key(app, "tone_btn_auto").proto.type == "primary"
    assert _button_by_key(app, "category_btn_travel").proto.type == "secondary"


def test_preselected_non_default_category_renders_as_primary_and_keeps_raw_value():
    """Regresyon: session_state'e (ör. görev geri yükleme akışından) ham bir
    enum değeri önceden set edilmişse, o kart Türkçe arayüzde bile doğru
    şekilde "seçili" (primary) render edilir -- ve run_pipeline()'a giden
    gerçek değer (session_state'in kendisi) hâlâ ham "healthy_living" kalır,
    çeviri katmanı hiçbir şeyi geri yazmaz.

    (Bunu GÖREV 1'in .select(ham_değer).run() yerine session_state'i
    ÖNCEDEN set edip .run() çağırma desenini kullanarak test ediyoruz --
    aynı desen burada da güvenli/doğru.)
    """
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "tr"
    app.session_state["documentary_topic_category"] = "healthy_living"
    app.run()

    assert app.session_state["documentary_topic_category"] == "healthy_living"

    selected_button = _button_by_key(app, "category_btn_healthy_living")
    assert selected_button.proto.type == "primary"
    assert selected_button.label == "🥗  Sağlıklı Yaşam"
    assert _button_by_key(app, "category_btn_auto").proto.type == "secondary"


def test_neutral_tone_preview_uses_fallback_description_not_misattributed_text():
    """Tone.neutral'ın PROFILE_PROMPTS'ta kendi girdisi yok (get_template()
    zaten Tone.credibility'ye düşüyor) -- kart önizlemesi bunu Credible'ın
    metnini sessizce ödünç almak yerine açıkça, dürüst bir fallback notuyla
    göstermeli.
    """
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    expected = _translation("en")["Tone Neutral Fallback Description"]
    captions = [c.value for c in app.caption]
    assert any(expected in cap for cap in captions)


# -----------------------------------------------------------------------------
# "Çoklu Karakter Sistemi" planı (kullanıcı onaylı): Character kart grid'i +
# Format'ın karakter seçiliyken "kids"a kilitlenmesi.
# -----------------------------------------------------------------------------


def test_character_cards_show_translated_labels_and_previews():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "tr"
    app.run()

    bao_button = _button_by_key(app, "character_btn_bao")
    assert bao_button.label == "🐼  Bao"

    mother_and_baby_button = _button_by_key(app, "character_btn_mother_and_baby")
    assert mother_and_baby_button.label == "🐦🐤  Anne Kuş & Yavrusu"


def test_default_character_selection_is_none_and_rendered_as_primary():
    # Regresyon garantisi: Kategori/Ton'un "auto" varsayılanıyla AYNI
    # desen, ama Character'ın varsayılanı "none" (bkz.
    # _render_selection_card'ın default_value parametresi).
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.run()

    assert _button_by_key(app, "character_btn_none").proto.type == "primary"
    assert _button_by_key(app, "character_btn_bao").proto.type == "secondary"


def test_selecting_a_character_locks_format_to_kids_and_disables_selectbox():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_character_selection"] = "bao"
    app.run()

    format_select = _selectbox_by_key(app, "documentary_format")
    assert format_select.value == "kids"
    assert format_select.disabled is True


def test_mother_and_baby_pair_also_locks_format_to_kids():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_character_selection"] = "mother_and_baby"
    app.run()

    format_select = _selectbox_by_key(app, "documentary_format")
    assert format_select.value == "kids"
    assert format_select.disabled is True


def test_no_character_selected_leaves_format_free_and_enabled():
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
    app.session_state["ui_language"] = "en"
    app.session_state["documentary_character_selection"] = "none"
    app.run()

    format_select = _selectbox_by_key(app, "documentary_format")
    assert format_select.value == "standard"
    assert format_select.disabled is False
