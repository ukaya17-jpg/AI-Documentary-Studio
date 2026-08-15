import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.audio import AudioTrack
from app.models.script import Script, ScriptLine
from app.departments.production import audio_renderer
from app.utils import utils


class _FakeAudioSegment:
    """Lightweight pydub.AudioSegment stand-in -- render_narration_by_scene()
    only ever calls .empty()/.from_file()/+=/len()/.export() on it, so a
    real ffmpeg decode isn't needed to test the offset/concatenation logic
    (matches this suite's existing convention of mocking TTS/ffmpeg at the
    boundary rather than exercising real audio codecs in unit tests).
    """

    converter = None

    def __init__(self, length_ms=0):
        self.length_ms = length_ms

    def __len__(self):
        return self.length_ms

    def __add__(self, other):
        return _FakeAudioSegment(self.length_ms + len(other))

    @classmethod
    def empty(cls):
        return cls(0)

    @classmethod
    def from_file(cls, path):
        # Every fake scene clip is a fixed 2.0s -- makes expected cumulative
        # offsets trivial to assert (0.0, 2.0, 4.0, ...).
        return cls(2000)

    def export(self, path, format=None):
        Path(path).write_bytes(b"fake-combined-mp3")
        return self


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


class TestRenderNarrationByScene(unittest.TestCase):
    """"Sahne Bazlı Gerçek Ses Değişimi" planı (kullanıcı onaylı): her
    script.lines[i] KENDİ casting_by_scene kaydının karakterine (varsa)
    göre AYRI bir TTS çağrısıyla üretilmeli, sonra tek bir audio.mp3/
    subtitle.srt'de birleştirilmeli.
    """

    def setUp(self):
        self.task_id = "test-audio-renderer-by-scene"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    def _fake_tts(self, **kwargs):
        Path(kwargs["voice_file"]).write_bytes(b"fake-scene-audio")
        return MagicMock()

    def _fake_create_subtitle(self, sub_maker, text, subtitle_file):
        Path(subtitle_file).write_text(f"1\n00:00:00,000 --> 00:00:01,000\n{text}\n")

    @patch("pydub.AudioSegment", _FakeAudioSegment)
    @patch("app.departments.production.audio_renderer.voice.merge_scene_subtitles", return_value=True)
    @patch("app.departments.production.audio_renderer.voice.create_subtitle")
    @patch("app.departments.production.audio_renderer.voice.tts")
    @patch("app.departments.production.audio_renderer.voice.parse_voice_name", side_effect=lambda v: v)
    def test_each_scene_uses_its_cast_characters_voice(
        self, mock_parse_voice_name, mock_tts, mock_create_subtitle, mock_merge
    ):
        from app.config import characters

        fake_registry = {
            "fake_a": ("Fake A", "fake_a", "elevenlabs:aaa:Voice A"),
            "fake_b": ("Fake B", "fake_b", "elevenlabs:bbb:Voice B"),
        }
        mock_tts.side_effect = self._fake_tts
        mock_create_subtitle.side_effect = self._fake_create_subtitle

        script = Script(
            full_text="Line zero.\n\nLine one.\n\nLine two.",
            lines=[
                ScriptLine(scene_index=0, text="Line zero."),
                ScriptLine(scene_index=1, text="Line one."),
                ScriptLine(scene_index=2, text="Line two."),
            ],
        )
        # Scene 0 -> Fake A's voice, scene 1 -> no character (falls back to
        # the general voice), scene 2 -> Fake B's voice (its "location"
        # entry, if any, must never affect voice selection -- only
        # "character" does, matching _resolve_narration_voice's semantics).
        casting_by_scene = {
            0: {"character": "fake_a", "location": None},
            1: {"character": None, "location": None},
            2: {"character": "fake_b", "location": "somewhere"},
        }

        with patch.dict(characters._CHARACTER_SLUGS, fake_registry, clear=True):
            track = audio_renderer.render_narration_by_scene(
                script, self.task_id, "tr-TR-AhmetNeural", casting_by_scene
            )

        self.assertEqual(mock_tts.call_count, 3)
        voices_used = [call.kwargs["voice_name"] for call in mock_tts.call_args_list]
        self.assertEqual(
            voices_used,
            ["elevenlabs:aaa:Voice A", "tr-TR-AhmetNeural", "elevenlabs:bbb:Voice B"],
        )

        self.assertTrue(track.voice_file.endswith("audio.mp3"))
        self.assertTrue(os.path.exists(track.voice_file))
        self.assertEqual(track.duration_seconds, 6.0)  # 3 scenes x fake 2.0s each

        # merge_scene_subtitles must see each scene's REAL cumulative start
        # offset in the merged track (0.0, 2.0, 4.0), not all starting at 0.
        merge_args, _ = mock_merge.call_args
        offsets = [offset for (_file, offset) in merge_args[0]]
        self.assertEqual(offsets, [0.0, 2.0, 4.0])

    @patch("pydub.AudioSegment", _FakeAudioSegment)
    @patch("app.departments.production.audio_renderer.voice.merge_scene_subtitles", return_value=True)
    @patch("app.departments.production.audio_renderer.voice.create_subtitle")
    @patch("app.departments.production.audio_renderer.voice.tts")
    @patch("app.departments.production.audio_renderer.voice.parse_voice_name", side_effect=lambda v: v)
    def test_cleans_up_per_scene_temp_files(
        self, mock_parse_voice_name, mock_tts, mock_create_subtitle, mock_merge
    ):
        mock_tts.side_effect = self._fake_tts
        mock_create_subtitle.side_effect = self._fake_create_subtitle

        script = Script(
            full_text="Line zero.",
            lines=[ScriptLine(scene_index=0, text="Line zero.")],
        )

        audio_renderer.render_narration_by_scene(
            script, self.task_id, "tr-TR-AhmetNeural", {0: {"character": None, "location": None}}
        )

        self.assertFalse(
            os.path.exists(os.path.join(self.task_directory, "audio_scene_0.mp3"))
        )
        self.assertFalse(
            os.path.exists(os.path.join(self.task_directory, "subtitle_scene_0.srt"))
        )

    @patch("app.departments.production.audio_renderer.voice.tts", return_value=None)
    @patch("app.departments.production.audio_renderer.voice.parse_voice_name", side_effect=lambda v: v)
    def test_raises_when_a_scenes_tts_fails(self, mock_parse_voice_name, mock_tts):
        script = Script(
            full_text="Line zero.",
            lines=[ScriptLine(scene_index=0, text="Line zero.")],
        )
        with self.assertRaises(RuntimeError):
            audio_renderer.render_narration_by_scene(
                script, self.task_id, "tr-TR-AhmetNeural", {}
            )


class TestRenderAudioPlanDispatch(unittest.TestCase):
    """render_audio_plan(), render_narration_by_scene()'e SADECE
    casting_by_scene en az bir sahnede gerçek bir karakter içeriyorsa
    dallanmalı -- her diğer durumda (regresyon garantisi) eskisi gibi
    render_narration() + _resolve_narration_voice() kullanılmalı.
    """

    def setUp(self):
        self.task_id = "test-audio-renderer-dispatch"
        self.task_directory = utils.task_dir(self.task_id)

    def tearDown(self):
        shutil.rmtree(self.task_directory, ignore_errors=True)

    @patch("app.departments.production.audio_renderer.render_narration_by_scene")
    @patch("app.departments.production.audio_renderer.render_narration")
    def test_falls_back_to_single_call_path_when_casting_by_scene_is_none(
        self, mock_render_narration, mock_render_by_scene
    ):
        script = Script(full_text="Text", lines=[ScriptLine(scene_index=0, text="Text")])
        mock_render_narration.return_value = AudioTrack()

        audio_renderer.render_audio_plan(
            script, self.task_id, "tr-TR-AhmetNeural", casting_by_scene=None
        )

        mock_render_narration.assert_called_once()
        mock_render_by_scene.assert_not_called()

    @patch("app.departments.production.audio_renderer.render_narration_by_scene")
    @patch("app.departments.production.audio_renderer.render_narration")
    def test_falls_back_to_single_call_path_when_auto_casting_picked_no_character_anywhere(
        self, mock_render_narration, mock_render_by_scene
    ):
        script = Script(full_text="Text", lines=[ScriptLine(scene_index=0, text="Text")])
        mock_render_narration.return_value = AudioTrack()
        casting_by_scene = {
            0: {"character": None, "location": "somewhere"},
            1: {"character": None, "location": None},
        }

        audio_renderer.render_audio_plan(
            script, self.task_id, "tr-TR-AhmetNeural", casting_by_scene=casting_by_scene
        )

        mock_render_narration.assert_called_once()
        mock_render_by_scene.assert_not_called()

    @patch("app.departments.production.audio_renderer.render_narration_by_scene")
    @patch("app.departments.production.audio_renderer.render_narration")
    def test_uses_per_scene_path_when_auto_casting_picked_a_character(
        self, mock_render_narration, mock_render_by_scene
    ):
        script = Script(full_text="Text", lines=[ScriptLine(scene_index=0, text="Text")])
        mock_render_by_scene.return_value = AudioTrack()
        casting_by_scene = {0: {"character": "fake_a", "location": None}}

        audio_renderer.render_audio_plan(
            script, self.task_id, "tr-TR-AhmetNeural", casting_by_scene=casting_by_scene
        )

        mock_render_by_scene.assert_called_once()
        mock_render_narration.assert_not_called()


class TestResolveNarrationVoice(unittest.TestCase):
    """"Karakter Sesi" planı (kullanıcı onaylı, Seçenek A): tam olarak TEK
    karakter seçiliyken anlatım O karakterin kayıtlı sesiyle okunmalı;
    karaktersiz ya da çoklu-karakter (ör. Anne+Yavru) durumlarda davranış
    HİÇ değişmemeli (regresyon garantisi).

    Registry temizliği (kullanıcı onaylı): üretim karakterleri (Bao vb.)
    kaldırıldığı için bu testler artık gerçek registry verisine değil,
    `unittest.mock.patch.dict` ile test süresince eklenen SAHTE bir
    registry'ye dayanıyor -- amaç aynı: mekanizmanın kendisini (belirli bir
    karakter isminin belirli bir sese eşlenmesini) registry boşken de
    doğrulamak. Yeni gerçek karakterler eklendiğinde bu testlerin
    değişmesine gerek yok.
    """

    def _character(self, name):
        from app.models.character import CharacterReference

        return CharacterReference(name=name, frontal_image_url="data:image/jpeg;base64,x")

    def test_no_character_references_keeps_the_given_voice(self):
        result = audio_renderer._resolve_narration_voice("tr-TR-AhmetNeural", None)
        self.assertEqual(result, "tr-TR-AhmetNeural")

    def test_empty_character_references_keeps_the_given_voice(self):
        result = audio_renderer._resolve_narration_voice("tr-TR-AhmetNeural", [])
        self.assertEqual(result, "tr-TR-AhmetNeural")

    def test_single_known_character_overrides_to_its_registered_voice(self):
        from app.config import characters

        fake_registry = {"fake_hero": ("Fake Hero", "fake_hero", "elevenlabs:xyz:Fake Voice")}
        with patch.dict(characters._CHARACTER_SLUGS, fake_registry, clear=True):
            result = audio_renderer._resolve_narration_voice(
                "tr-TR-AhmetNeural", [self._character("Fake Hero")]
            )
        self.assertEqual(result, "elevenlabs:xyz:Fake Voice")
        self.assertNotEqual(result, "tr-TR-AhmetNeural")

    def test_different_single_characters_produce_different_voices(self):
        from app.config import characters

        fake_registry = {
            "fake_a": ("Fake A", "fake_a", "elevenlabs:aaa:Voice A"),
            "fake_b": ("Fake B", "fake_b", "elevenlabs:bbb:Voice B"),
        }
        with patch.dict(characters._CHARACTER_SLUGS, fake_registry, clear=True):
            voice_a = audio_renderer._resolve_narration_voice("x", [self._character("Fake A")])
            voice_b = audio_renderer._resolve_narration_voice("x", [self._character("Fake B")])
        self.assertNotEqual(voice_a, voice_b)

    def test_multi_character_scene_keeps_the_given_voice(self):
        # "Çoklu Karakter Sistemi" planı (kullanıcı onaylı): anne+yavru gibi
        # sahnelerde HANGİ karakterin sesi kullanılacağı BİLİNÇLİ OLARAK bu
        # turun kapsamı dışında -- davranış hiç değişmemeli.
        result = audio_renderer._resolve_narration_voice(
            "tr-TR-AhmetNeural",
            [self._character("Mother"), self._character("Baby")],
        )
        self.assertEqual(result, "tr-TR-AhmetNeural")

    def test_unregistered_character_reference_keeps_the_given_voice(self):
        result = audio_renderer._resolve_narration_voice(
            "tr-TR-AhmetNeural", [self._character("Nobody")]
        )
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

        # Registry temizliği (kullanıcı onaylı): "bao" artık kayıtlı değil
        # -- test süresince sahte bir karakter enjekte edilip mekanizma
        # (registry boşken de) doğrulanıyor, bkz. TestResolveNarrationVoice.
        fake_registry = {"fake_hero": ("Fake Hero", "fake_hero", "elevenlabs:xyz:Fake Voice")}
        mock_tts.return_value = MagicMock()
        script = Script(full_text="Fake Hero shares his bamboo.")
        fake_hero = CharacterReference(
            name="Fake Hero", frontal_image_url="data:image/jpeg;base64,x"
        )

        with patch.dict(characters._CHARACTER_SLUGS, fake_registry, clear=True):
            audio_plan = audio_renderer.render_audio_plan(
                script,
                self.task_id,
                voice_name="tr-TR-AhmetNeural",
                character_references=[fake_hero],
            )
            expected_voice = characters.get_character_voice_name("fake_hero")

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
