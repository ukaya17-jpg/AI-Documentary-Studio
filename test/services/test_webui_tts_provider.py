import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.models.documentary_project import DocumentaryProject
from app.models.research_plan import ResearchPlan
from app.pipeline import default_pipeline
from app.services import voice

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"

# ADIM 2 (Provider Sistemi keşif raporu, kullanıcı onaylı): voice.tts()
# servis katmanında zaten 7 sağlayıcıyı (Azure v1/v2, SiliconFlow, Gemini,
# MiMo, ElevenLabs, Chatterbox) destekliyordu -- Documentary Studio'nun
# "Ses Adı" alanı düz bir metin girdisiydi, kullanıcı doğru önekli
# voice_name string'ini el ile yazmak zorundaydı. Bu, Klasik Mod'un
# _render_audio_settings()'inin Documentary Studio'ya özel karşılığını
# test ediyor. GÖREV 1'den bilinen kısıt burada da geçerli: bu sayfada
# HERHANGİ bir ikinci .run() format_func'lı selectbox'ları kırıyor -- her
# test tek bir .run() ile, session_state önceden set edilerek doğrulanıyor.


def _widget_by_key(widgets, key):
    return next(w for w in widgets if str(getattr(w, "key", "")) == key)


def _clean_ui_config(**overrides):
    return dict(config.ui, tts_server="azure-tts-v1", voice_name="", **overrides)


def _mock_voice_lists(stack, *, azure=("en-US-JennyNeural",), elevenlabs=()):
    stack.enter_context(patch.object(voice, "get_all_azure_voices", return_value=list(azure)))
    stack.enter_context(patch.object(voice, "get_siliconflow_voices", return_value=[]))
    stack.enter_context(patch.object(voice, "get_gemini_voices", return_value=[]))
    stack.enter_context(patch.object(voice, "get_mimo_voices", return_value=[]))
    stack.enter_context(
        patch.object(voice, "get_elevenlabs_voices", return_value=list(elevenlabs))
    )
    stack.enter_context(patch.object(voice, "get_chatterbox_voices", return_value=[]))


def _run_app(*, extra_session_state=None, ui_overrides=None, azure=("en-US-JennyNeural",), elevenlabs=()):
    test_ui = _clean_ui_config(**(ui_overrides or {}))
    with ExitStack() as stack:
        stack.enter_context(patch.object(config, "ui", test_ui))
        stack.enter_context(patch.object(config, "save_config"))
        _mock_voice_lists(stack, azure=azure, elevenlabs=elevenlabs)
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        for key, value in (extra_session_state or {}).items():
            app.session_state[key] = value
        app.run()
    return app


def test_default_server_is_azure_v1_with_no_extra_credential_inputs():
    app = _run_app()

    assert not app.exception
    server_select = _widget_by_key(app.selectbox, "documentary_tts_server_select")
    assert server_select.value == "azure-tts-v1"
    assert not any(
        str(getattr(w, "key", "")).startswith("documentary_azure_speech_")
        for w in app.text_input
    )
    assert not any(
        str(getattr(w, "key", "")) == "documentary_gemini_tts_api_key_input"
        for w in app.text_input
    )


def test_azure_v2_shows_speech_region_and_key_inputs():
    app = _run_app(
        extra_session_state={"documentary_tts_server_select": "azure-tts-v2"}
    )

    assert not app.exception
    assert any(
        str(getattr(w, "key", "")) == "documentary_azure_speech_region_input"
        for w in app.text_input
    )
    key_input = _widget_by_key(app.text_input, "documentary_azure_speech_key_input")
    assert key_input.proto.type == key_input.proto.PASSWORD


def test_gemini_shows_gemini_api_key_input():
    app = _run_app(
        extra_session_state={"documentary_tts_server_select": "gemini-tts"}
    )

    assert not app.exception
    key_input = _widget_by_key(
        app.text_input, "documentary_gemini_tts_api_key_input"
    )
    assert key_input.proto.type == key_input.proto.PASSWORD


def test_siliconflow_shows_siliconflow_api_key_input():
    app = _run_app(
        extra_session_state={"documentary_tts_server_select": "siliconflow"}
    )

    assert not app.exception
    assert any(
        str(getattr(w, "key", "")) == "documentary_siliconflow_api_key_input"
        for w in app.text_input
    )


def test_mimo_shows_mimo_api_key_input():
    app = _run_app(
        extra_session_state={"documentary_tts_server_select": "mimo-tts"}
    )

    assert not app.exception
    assert any(
        str(getattr(w, "key", "")) == "documentary_mimo_tts_api_key_input"
        for w in app.text_input
    )


def test_chatterbox_shows_base_url_input():
    app = _run_app(
        extra_session_state={"documentary_tts_server_select": "chatterbox"}
    )

    assert not app.exception
    assert any(
        str(getattr(w, "key", "")) == "documentary_chatterbox_base_url_input"
        for w in app.text_input
    )


def test_elevenlabs_shows_api_key_input_and_lists_fetched_voices():
    app = _run_app(
        extra_session_state={"documentary_tts_server_select": "elevenlabs"},
        azure=(),
        elevenlabs=("elevenlabs:abc123:Test Voice",),
    )

    assert not app.exception
    assert any(
        str(getattr(w, "key", "")) == "documentary_elevenlabs_api_key_input"
        for w in app.text_input
    )
    voice_select = next(
        w
        for w in app.selectbox
        if str(getattr(w, "key", "")).startswith("documentary_voice_select_elevenlabs")
    )
    assert voice_select.value == "elevenlabs:abc123:Test Voice"


def test_no_voices_available_shows_warning_instead_of_crashing():
    app = _run_app(azure=())

    assert not app.exception
    assert any(
        "No voices available for the selected TTS server" in w.value
        for w in app.warning
    )


def _fake_project():
    project = DocumentaryProject(
        project_id="fake-id",
        topic="Test Topic",
        research_plan=ResearchPlan(topic="Test Topic"),
    )
    project.final_video_path = ""
    return project


def test_generate_passes_selected_voice_name_to_run_pipeline():
    test_ui = _clean_ui_config()
    with ExitStack() as stack:
        stack.enter_context(patch.object(config, "ui", test_ui))
        stack.enter_context(patch.object(config, "save_config"))
        _mock_voice_lists(stack, azure=("en-US-JennyNeural",))
        run_mock = stack.enter_context(
            patch.object(default_pipeline, "run_pipeline", return_value=_fake_project())
        )
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "en"
        app.session_state["documentary_topic"] = "Test Topic"
        app.session_state["documentary_generate_button"] = True
        app.run()

    assert not app.exception
    run_mock.assert_called_once()
    assert run_mock.call_args.kwargs["voice_name"] == "en-US-JennyNeural"
