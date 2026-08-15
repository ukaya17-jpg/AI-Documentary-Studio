import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.departments.creative import casting_generator
from app.models.script import Script, ScriptLine
from app.models.storyboard import Storyboard, StoryboardShot


def _storyboard():
    return Storyboard(
        shots=[
            StoryboardShot(scene_index=0, description="a chemistry experiment"),
            StoryboardShot(scene_index=1, description="looking at the stars"),
        ]
    )


def _script():
    return Script(
        full_text="Mixing chemicals safely.\n\nExploring the night sky.",
        lines=[
            ScriptLine(scene_index=0, text="Mixing chemicals safely."),
            ScriptLine(scene_index=1, text="Exploring the night sky."),
        ],
    )


class TestBuildCastingPrompt(unittest.TestCase):
    def test_prompt_includes_scene_narration_and_catalogs(self):
        prompt = casting_generator.build_casting_prompt(
            _storyboard(),
            _script(),
            {"professor_nova": "a science teacher"},
            {"kimya_laboratuvari": "a chemistry lab"},
        )
        self.assertIn("Mixing chemicals safely.", prompt)
        self.assertIn("Exploring the night sky.", prompt)
        self.assertIn("professor_nova: a science teacher", prompt)
        self.assertIn("kimya_laboratuvari: a chemistry lab", prompt)

    def test_empty_catalogs_produce_a_null_only_placeholder(self):
        prompt = casting_generator.build_casting_prompt(_storyboard(), _script(), {}, {})
        self.assertIn("katalog boş", prompt)

    def test_prompt_mentions_the_max_characters_cap(self):
        # "Çoklu Karakter Aynı Sahnede" planı: prompt LLM'e kaç karaktere
        # kadar seçebileceğini açıkça söylemeli -- kod içindeki gerçek
        # sınırla (casting_generator._MAX_CHARACTERS_PER_SCENE) tutarlı.
        prompt = casting_generator.build_casting_prompt(
            _storyboard(), _script(), {"professor_nova": "x"}, {}
        )
        self.assertIn(str(casting_generator._MAX_CHARACTERS_PER_SCENE), prompt)


class TestGenerateCastingPlan(unittest.TestCase):
    def test_empty_storyboard_returns_empty_dict_without_calling_llm(self):
        with patch(
            "app.departments.creative.casting_generator.generate_json"
        ) as mock_generate_json:
            result = casting_generator.generate_casting_plan(
                Storyboard(shots=[]), _script(), {"a": "b"}, {"c": "d"}
            )
        self.assertEqual(result, {})
        mock_generate_json.assert_not_called()

    def test_empty_catalogs_return_empty_dict_without_calling_llm(self):
        # Karakter/mekan boyutlarının İKİSİ de auto değilken (katalog boş
        # geldiyse) LLM'e hiç gidilmemeli -- gereksiz maliyet.
        with patch(
            "app.departments.creative.casting_generator.generate_json"
        ) as mock_generate_json:
            result = casting_generator.generate_casting_plan(_storyboard(), _script(), {}, {})
        self.assertEqual(result, {})
        mock_generate_json.assert_not_called()

    def test_parses_valid_llm_response(self):
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={
                "casting": [
                    {
                        "scene_index": 0,
                        "characters": ["professor_nova"],
                        "location": "kimya_laboratuvari",
                    },
                    {"scene_index": 1, "characters": [], "location": "gozlemevi"},
                ]
            },
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(),
                _script(),
                {"professor_nova": "x"},
                {"kimya_laboratuvari": "y", "gozlemevi": "z"},
            )
        self.assertEqual(
            result,
            {
                0: {"characters": ["professor_nova"], "location": "kimya_laboratuvari"},
                1: {"characters": [], "location": "gozlemevi"},
            },
        )

    def test_parses_multiple_characters_in_priority_order(self):
        # "Çoklu Karakter Aynı Sahnede" planı (kullanıcı onaylı): bir sahnede
        # 2+ karakter aynı anda görünebilir -- liste sırası korunmalı (ilk
        # eleman = en yüksek öncelik, bkz. audio_renderer'ın ses seçimi).
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={
                "casting": [
                    {
                        "scene_index": 0,
                        "characters": ["professor_nova", "robo"],
                        "location": None,
                    },
                ]
            },
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(), _script(), {"professor_nova": "x", "robo": "y"}, {}
            )
        self.assertEqual(result[0]["characters"], ["professor_nova", "robo"])

    def test_caps_characters_at_the_max_and_logs_a_warning(self):
        # fal.ai Kling O1'in elements[] sınırı (bkz. docs/character-
        # consistency-research.md) -- LLM kataloğu bilse bile fazla karakter
        # istemişse, en düşük öncelikliler (liste sonu) sessizce düşürülmeli.
        four_characters = ["professor_nova", "robo", "luna", "atom"]
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={
                "casting": [{"scene_index": 0, "characters": four_characters, "location": None}]
            },
        ), patch("app.departments.creative.casting_generator.logger") as mock_logger:
            result = casting_generator.generate_casting_plan(
                _storyboard(),
                _script(),
                {slug: slug for slug in four_characters},
                {},
            )
        self.assertEqual(
            result[0]["characters"],
            four_characters[: casting_generator._MAX_CHARACTERS_PER_SCENE],
        )
        mock_logger.warning.assert_called_once()

    def test_hallucinated_slug_is_dropped_not_raised(self):
        # LLM kataloğu bilmediği bir slug uydurursa (ör. eski kaldırılmış
        # bir karakter) sessizce düşmeli -- çökmemeli.
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={
                "casting": [
                    {"scene_index": 0, "characters": ["bao"], "location": "made_up_place"},
                ]
            },
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(), _script(), {"professor_nova": "x"}, {"kimya_laboratuvari": "y"}
            )
        self.assertEqual(result[0], {"characters": [], "location": None})

    def test_hallucinated_slug_among_valid_ones_is_dropped_but_valid_ones_kept(self):
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={
                "casting": [
                    {"scene_index": 0, "characters": ["professor_nova", "bao", "robo"], "location": None},
                ]
            },
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(), _script(), {"professor_nova": "x", "robo": "y"}, {}
            )
        self.assertEqual(result[0]["characters"], ["professor_nova", "robo"])

    def test_scenes_missing_from_llm_response_default_to_null(self):
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={
                "casting": [{"scene_index": 0, "characters": ["professor_nova"], "location": None}]
            },
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(), _script(), {"professor_nova": "x"}, {}
            )
        # scene_index 1 hiç bahsedilmedi ama storyboard'da var -- yine de
        # sözlükte bir girişi olmalı (asset_generator her scene_index için
        # bir giriş bulmayı bekliyor).
        self.assertIn(1, result)
        self.assertEqual(result[1], {"characters": [], "location": None})

    def test_malformed_items_are_skipped(self):
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={"casting": ["not a dict", {"scene_index": "not an int"}, {}]},
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(), _script(), {"professor_nova": "x"}, {}
            )
        # Hiçbiri geçerli parse edilemedi -- her iki sahne de varsayılan
        # boş girişle sonuçlanmalı, exception FIRLAMAMALI.
        self.assertEqual(result[0], {"characters": [], "location": None})
        self.assertEqual(result[1], {"characters": [], "location": None})

    def test_non_list_characters_field_is_treated_as_empty(self):
        # LLM yanlışlıkla eski tekil "character": "professor_nova" biçimini
        # döndürürse (liste DEĞİL) çökmemeli, boş listeye düşmeli.
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={
                "casting": [{"scene_index": 0, "characters": "professor_nova", "location": None}]
            },
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(), _script(), {"professor_nova": "x"}, {}
            )
        self.assertEqual(result[0]["characters"], [])


if __name__ == "__main__":
    unittest.main()
