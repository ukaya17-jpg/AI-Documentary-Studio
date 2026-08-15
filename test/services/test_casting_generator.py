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
                    {"scene_index": 0, "character": "professor_nova", "location": "kimya_laboratuvari"},
                    {"scene_index": 1, "character": None, "location": "gozlemevi"},
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
                0: {"character": "professor_nova", "location": "kimya_laboratuvari"},
                1: {"character": None, "location": "gozlemevi"},
            },
        )

    def test_hallucinated_slug_is_dropped_not_raised(self):
        # LLM kataloğu bilmediği bir slug uydurursa (ör. eski kaldırılmış
        # bir karakter) sessizce None'a düşmeli -- çökmemeli.
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={
                "casting": [
                    {"scene_index": 0, "character": "bao", "location": "made_up_place"},
                ]
            },
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(), _script(), {"professor_nova": "x"}, {"kimya_laboratuvari": "y"}
            )
        self.assertEqual(result[0], {"character": None, "location": None})

    def test_scenes_missing_from_llm_response_default_to_null(self):
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={"casting": [{"scene_index": 0, "character": "professor_nova", "location": None}]},
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(), _script(), {"professor_nova": "x"}, {}
            )
        # scene_index 1 hiç bahsedilmedi ama storyboard'da var -- yine de
        # sözlükte bir girişi olmalı (asset_generator her scene_index için
        # bir giriş bulmayı bekliyor).
        self.assertIn(1, result)
        self.assertEqual(result[1], {"character": None, "location": None})

    def test_malformed_items_are_skipped(self):
        with patch(
            "app.departments.creative.casting_generator.generate_json",
            return_value={"casting": ["not a dict", {"scene_index": "not an int"}, {}]},
        ):
            result = casting_generator.generate_casting_plan(
                _storyboard(), _script(), {"professor_nova": "x"}, {}
            )
        # Hiçbiri geçerli parse edilemedi -- her iki sahne de varsayılan
        # null girişle sonuçlanmalı, exception FIRLAMAMALI.
        self.assertEqual(result[0], {"character": None, "location": None})
        self.assertEqual(result[1], {"character": None, "location": None})


if __name__ == "__main__":
    unittest.main()
