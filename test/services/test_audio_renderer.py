import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.script import Script
from app.departments.production import audio_renderer
from app.utils import utils


class TestRenderNarration(unittest.TestCase):
    def setUp(self):
        self.task_id = "test-audio-renderer"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    @patch("app.departments.production.audio_renderer.voice.create_subtitle")
    @patch("app.departments.production.audio_renderer.voice.get_audio_duration", return_value=12.5)
    @patch("app.departments.production.audio_renderer.voice.tts")
    @patch("app.departments.production.audio_renderer.voice.parse_voice_name", side_effect=lambda v: v)
    def test_builds_audio_track_from_tts_result(
        self, mock_parse_voice_name, mock_tts, mock_get_duration, mock_create_subtitle
    ):
        mock_tts.return_value = MagicMock()

        def fake_create_subtitle(sub_maker, text, subtitle_file):
            Path(subtitle_file).write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n")

        mock_create_subtitle.side_effect = fake_create_subtitle

        script = Script(full_text="Rome was not built in a day.")
        track = audio_renderer.render_narration(script, self.task_id, "tr-TR-AhmetNeural")

        self.assertEqual(track.voice_name, "tr-TR-AhmetNeural")
        self.assertTrue(track.voice_file.endswith("audio.mp3"))
        self.assertTrue(track.subtitle_file.endswith("subtitle.srt"))
        self.assertEqual(track.duration_seconds, 12.5)
        mock_tts.assert_called_once()
        _, kwargs = mock_tts.call_args
        self.assertEqual(kwargs["text"], "Rome was not built in a day.")

    @patch("app.departments.production.audio_renderer.voice.tts", return_value=None)
    @patch("app.departments.production.audio_renderer.voice.parse_voice_name", side_effect=lambda v: v)
    def test_raises_when_tts_fails(self, mock_parse_voice_name, mock_tts):
        script = Script(full_text="Text")
        with self.assertRaises(RuntimeError):
            audio_renderer.render_narration(script, self.task_id, "tr-TR-AhmetNeural")


class TestResolveNarrationVoice(unittest.TestCase):
    """"Karakter Sesi" planı (kullanıcı onaylı, Seçenek A): tam olarak TEK
    karakter seçiliyken anlatım O karakterin kayıtlı sesiyle okunmalı;
    karaktersiz ya da çoklu-karakter (ör. Anne+Yavru) durumlarda davranış
    HİÇ değişmemeli (regresyon garantisi).
    """

    def _bao(self):
        from app.models.character import CharacterReference

        return CharacterReference(name="Bao", frontal_image_url="data:image/jpeg;base64,x")

    def _mother_bird(self):
        from app.models.character import CharacterReference

        return CharacterReference(name="Mother Bird", frontal_image_url="data:image/jpeg;base64,x")

    def _little_blue_bird(self):
        from app.models.character import CharacterReference

        return CharacterReference(
            name="Little Blue Bird", frontal_image_url="data:image/jpeg;base64,x"
        )

    def test_no_character_references_keeps_the_given_voice(self):
        result = audio_renderer._resolve_narration_voice("tr-TR-AhmetNeural", None)
        self.assertEqual(result, "tr-TR-AhmetNeural")

    def test_empty_character_references_keeps_the_given_voice(self):
        result = audio_renderer._resolve_narration_voice("tr-TR-AhmetNeural", [])
        self.assertEqual(result, "tr-TR-AhmetNeural")

    def test_single_known_character_overrides_to_its_registered_voice(self):
        from app.config import characters

        result = audio_renderer._resolve_narration_voice("tr-TR-AhmetNeural", [self._bao()])
        self.assertEqual(result, characters.get_character_voice_name("bao"))
        self.assertNotEqual(result, "tr-TR-AhmetNeural")

    def test_different_single_characters_produce_different_voices(self):
        bao_voice = audio_renderer._resolve_narration_voice("x", [self._bao()])
        mother_voice = audio_renderer._resolve_narration_voice("x", [self._mother_bird()])
        self.assertNotEqual(bao_voice, mother_voice)

    def test_multi_character_scene_keeps_the_given_voice(self):
        # "Çoklu Karakter Sistemi" planı (kullanıcı onaylı): anne+yavru gibi
        # sahnelerde HANGİ karakterin sesi kullanılacağı BİLİNÇLİ OLARAK bu
        # turun kapsamı dışında -- davranış hiç değişmemeli.
        result = audio_renderer._resolve_narration_voice(
            "tr-TR-AhmetNeural", [self._mother_bird(), self._little_blue_bird()]
        )
        self.assertEqual(result, "tr-TR-AhmetNeural")

    def test_unregistered_character_reference_keeps_the_given_voice(self):
        from app.models.character import CharacterReference

        unknown = CharacterReference(name="Nobody", frontal_image_url="data:image/jpeg;base64,x")
        result = audio_renderer._resolve_narration_voice("tr-TR-AhmetNeural", [unknown])
        self.assertEqual(result, "tr-TR-AhmetNeural")


class TestRenderAudioPlan(unittest.TestCase):
    def setUp(self):
        self.task_id = "test-audio-renderer-plan"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    @patch("app.departments.production.audio_renderer.voice.create_subtitle")
    @patch("app.departments.production.audio_renderer.voice.get_audio_duration", return_value=5.0)
    @patch("app.departments.production.audio_renderer.voice.tts")
    @patch("app.departments.production.audio_renderer.voice.parse_voice_name", side_effect=lambda v: v)
    def test_single_character_reference_overrides_narration_voice(
        self, mock_parse_voice_name, mock_tts, mock_get_duration, mock_create_subtitle
    ):
        from app.config import characters
        from app.models.character import CharacterReference

        mock_tts.return_value = MagicMock()
        script = Script(full_text="Bao shares his bamboo.")
        bao = CharacterReference(name="Bao", frontal_image_url="data:image/jpeg;base64,x")

        audio_plan = audio_renderer.render_audio_plan(
            script,
            self.task_id,
            voice_name="tr-TR-AhmetNeural",
            character_references=[bao],
        )

        expected_voice = characters.get_character_voice_name("bao")
        self.assertEqual(audio_plan.narration.voice_name, expected_voice)
        mock_parse_voice_name.assert_called_once_with(expected_voice)

    @patch("app.departments.production.audio_renderer.voice.create_subtitle")
    @patch("app.departments.production.audio_renderer.voice.get_audio_duration", return_value=5.0)
    @patch("app.departments.production.audio_renderer.voice.tts")
    @patch("app.departments.production.audio_renderer.voice.parse_voice_name", side_effect=lambda v: v)
    def test_no_character_references_uses_the_requested_voice_unchanged(
        self, mock_parse_voice_name, mock_tts, mock_get_duration, mock_create_subtitle
    ):
        mock_tts.return_value = MagicMock()
        script = Script(full_text="A history documentary narration.")

        audio_plan = audio_renderer.render_audio_plan(
            script, self.task_id, voice_name="tr-TR-AhmetNeural"
        )

        self.assertEqual(audio_plan.narration.voice_name, "tr-TR-AhmetNeural")


if __name__ == "__main__":
    unittest.main()
