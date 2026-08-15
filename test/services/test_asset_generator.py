import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import TopicCategory
from app.models.character import CharacterReference
from app.models.script import Script, ScriptLine
from app.models.storyboard import Storyboard, StoryboardShot
from app.departments.production import asset_generator


def _words(n: int) -> str:
    return " ".join(["word"] * n)


class TestBuildAssetPlan(unittest.TestCase):
    def test_uses_first_search_term_per_shot(self):
        storyboard = Storyboard(
            shots=[
                StoryboardShot(scene_index=0, description="ruins", search_terms=["ancient ruins", "rome"]),
                StoryboardShot(scene_index=1, description="battle", search_terms=["battle field"]),
            ]
        )
        plan = asset_generator.build_asset_plan(storyboard)
        self.assertEqual(len(plan.candidates), 2)
        self.assertEqual(plan.candidates[0].search_term, "ancient ruins")
        self.assertEqual(plan.candidates[0].scene_index, 0)
        self.assertEqual(plan.candidates[1].search_term, "battle field")

    def test_falls_back_to_description_when_no_search_terms(self):
        storyboard = Storyboard(shots=[StoryboardShot(scene_index=0, description="a lone ruin", search_terms=[])])
        plan = asset_generator.build_asset_plan(storyboard)
        self.assertEqual(plan.candidates[0].search_term, "a lone ruin")

    def test_uses_provider_override(self):
        storyboard = Storyboard(shots=[StoryboardShot(scene_index=0, search_terms=["x"])])
        plan = asset_generator.build_asset_plan(storyboard, provider="pixabay")
        self.assertEqual(plan.candidates[0].provider, "pixabay")

    def test_empty_storyboard_yields_empty_plan(self):
        plan = asset_generator.build_asset_plan(Storyboard(shots=[]))
        self.assertEqual(plan.candidates, [])

    def test_ai_generated_provider_uses_description_as_prompt_not_search_term(self):
        # AI video path needs a descriptive generative-model prompt, not a
        # stock-search keyword phrase -- search_terms is deliberately unused here.
        storyboard = Storyboard(
            shots=[
                StoryboardShot(
                    scene_index=0,
                    description="a wide shot of ancient ruins at golden hour",
                    shot_type="wide",
                    search_terms=["ancient ruins", "golden hour"],
                )
            ]
        )
        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated")

        self.assertEqual(plan.candidates[0].provider, "ai_generated")
        self.assertEqual(plan.candidates[0].search_term, "")
        self.assertEqual(
            plan.candidates[0].prompt, "wide: a wide shot of ancient ruins at golden hour"
        )

    def test_ai_generated_provider_omits_shot_type_prefix_when_missing(self):
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a lone ruin", shot_type="")]
        )
        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated")

        self.assertEqual(plan.candidates[0].prompt, "a lone ruin")

    def test_ai_generated_prompt_includes_likeness_guard_for_film_highlights(self):
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a dramatic on-set moment")]
        )
        plan = asset_generator.build_asset_plan(
            storyboard, provider="ai_generated", topic_category=TopicCategory.film_highlights
        )

        self.assertIn("a dramatic on-set moment", plan.candidates[0].prompt)
        self.assertIn("Avoid recreating the likeness", plan.candidates[0].prompt)

    def test_ai_generated_prompt_omits_likeness_guard_for_other_categories(self):
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a wide shot of a coral reef")]
        )
        plan = asset_generator.build_asset_plan(
            storyboard, provider="ai_generated", topic_category=TopicCategory.marine
        )

        self.assertNotIn("Avoid recreating the likeness", plan.candidates[0].prompt)

    # "Tekrar eden kare" düzeltmesi: her sahnenin GERÇEK script metninden
    # (Pacing'in üretim-öncesi hedefinden değil) hesaplanan, sahne-bazlı
    # Kling duration seçimi.

    def test_ai_generated_defaults_to_5_when_no_script_given(self):
        # Regresyon garantisi: script=None -> mevcut davranış (hep "5")
        # hiç değişmemeli.
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a lone ruin")]
        )
        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated")

        self.assertEqual(plan.candidates[0].ai_duration, "5")

    def test_ai_generated_uses_5_for_a_scene_within_word_budget(self):
        # 11 kelime / 2.3 kelime-sn ~= 4.78s -- 5s sınırının altında.
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a lone ruin")]
        )
        script = Script(lines=[ScriptLine(scene_index=0, text=_words(11))])

        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated", script=script)

        self.assertEqual(plan.candidates[0].ai_duration, "5")

    def test_ai_generated_rounds_up_to_10_for_a_scene_over_word_budget(self):
        # 12 kelime / 2.3 kelime-sn ~= 5.22s -- 5s sınırını aşıyor, "10"a
        # yuvarlanmalı (aşağı yuvarlarsak tekrar eden kare riski geri gelir).
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a lone ruin")]
        )
        script = Script(lines=[ScriptLine(scene_index=0, text=_words(12))])

        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated", script=script)

        self.assertEqual(plan.candidates[0].ai_duration, "10")

    def test_ai_generated_selects_duration_independently_per_scene(self):
        # Sadece GERÇEKTEN ihtiyacı olan sahne "10" ödesin -- kısa kalan
        # sahne "5"te kalmalı (maliyet artışı sadece gereken yerde).
        storyboard = Storyboard(
            shots=[
                StoryboardShot(scene_index=0, description="short scene"),
                StoryboardShot(scene_index=1, description="long scene"),
            ]
        )
        script = Script(
            lines=[
                ScriptLine(scene_index=0, text=_words(11)),
                ScriptLine(scene_index=1, text=_words(12)),
            ]
        )

        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated", script=script)

        self.assertEqual(plan.candidates[0].ai_duration, "5")
        self.assertEqual(plan.candidates[1].ai_duration, "10")

    def test_ai_generated_falls_back_to_5_when_scene_has_no_matching_script_line(self):
        # script verilmiş ama bu sahne için hiç satır yoksa (kenar durum) --
        # çökmemeli, güvenli varsayılan "5"e düşmeli.
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=5, description="an orphan scene")]
        )
        script = Script(lines=[ScriptLine(scene_index=0, text=_words(20))])

        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated", script=script)

        self.assertEqual(plan.candidates[0].ai_duration, "5")

    def test_stock_provider_ignores_script_entirely(self):
        # script verilse bile stok yolu bundan hiç etkilenmemeli -- ai_duration
        # zaten stok candidate'lerinde anlamsız, search_term davranışı da
        # değişmemeli.
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="ruins", search_terms=["ancient ruins"])]
        )
        script = Script(lines=[ScriptLine(scene_index=0, text=_words(50))])

        plan = asset_generator.build_asset_plan(storyboard, provider="pexels", script=script)

        self.assertEqual(plan.candidates[0].search_term, "ancient ruins")
        self.assertEqual(plan.candidates[0].ai_duration, "5")


class TestCharacterReferencePrefix(unittest.TestCase):
    """"Bao" planı (kullanıcı onaylı): character_references verildiğinde her
    AI-video prompt'una "@Element1" öneki eklenmeli -- Kling O1'in
    elements[] listesini bu şekilde referans göstermesi ZORUNLU, aksi halde
    görmezden gelinir (bkz. docs/character-consistency-research.md).

    "Çoklu Karakter Sistemi" planı (kullanıcı onaylı): parametre tekil
    character_reference'tan listeye (character_references) genelleşti --
    tek karakterli testler burada BİLEREK 1 elemanlı liste kullanıyor, tam
    olarak eski davranışı (byte-identical prompt) kilitlemek için.
    """

    def _character(self, name: str = "Bao") -> CharacterReference:
        return CharacterReference(
            name=name,
            frontal_image_url="data:image/jpeg;base64,front",
            reference_image_urls=["data:image/jpeg;base64,threeq"],
        )

    def test_prefixes_ai_generated_prompt_with_element_reference(self):
        storyboard = Storyboard(
            shots=[
                StoryboardShot(
                    scene_index=0, description="walking through a bamboo forest", shot_type="wide"
                )
            ]
        )
        plan = asset_generator.build_asset_plan(
            storyboard, provider="ai_generated", character_references_by_scene={0: [self._character()]}
        )

        self.assertEqual(
            plan.candidates[0].prompt,
            "Take @Element1 as Bao. wide: walking through a bamboo forest",
        )

    def test_no_prefix_when_character_references_omitted(self):
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a lone ruin")]
        )
        plan = asset_generator.build_asset_plan(storyboard, provider="ai_generated")

        self.assertNotIn("@Element1", plan.candidates[0].prompt)

    def test_no_prefix_when_character_references_is_empty_list(self):
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a lone ruin")]
        )
        plan = asset_generator.build_asset_plan(
            storyboard, provider="ai_generated", character_references_by_scene={0: []}
        )

        self.assertNotIn("@Element1", plan.candidates[0].prompt)

    def test_no_prefix_for_stock_provider_even_with_character_references(self):
        # Karakter referansı sadece AI-video prompt'una anlamlı -- stok
        # search_term'e sızmamalı.
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="ruins", search_terms=["ancient ruins"])]
        )
        plan = asset_generator.build_asset_plan(
            storyboard, provider="pexels", character_references_by_scene={0: [self._character()]}
        )

        self.assertEqual(plan.candidates[0].search_term, "ancient ruins")

    def test_character_prefix_coexists_with_film_highlights_likeness_guard(self):
        storyboard = Storyboard(
            shots=[StoryboardShot(scene_index=0, description="a dramatic on-set moment")]
        )
        plan = asset_generator.build_asset_plan(
            storyboard,
            provider="ai_generated",
            topic_category=TopicCategory.film_highlights,
            character_references_by_scene={0: [self._character()]},
        )

        self.assertIn("@Element1 as Bao", plan.candidates[0].prompt)
        self.assertIn("Avoid recreating the likeness", plan.candidates[0].prompt)

    def test_two_characters_are_addressed_as_element1_and_element2(self):
        # "Çoklu Karakter Sistemi" planı: anne+yavru gibi aynı sahnede
        # birden fazla karakter -- fal.ai'nin kendi resmi elements[]
        # örneğiyle aynı desen ("@Element1... @Element2...").
        storyboard = Storyboard(
            shots=[
                StoryboardShot(
                    scene_index=0,
                    description="feeding her chick a worm",
                    shot_type="close-up",
                )
            ]
        )
        plan = asset_generator.build_asset_plan(
            storyboard,
            provider="ai_generated",
            character_references_by_scene={
                0: [
                    self._character("Mother Bird"),
                    self._character("Little Blue Bird"),
                ]
            },
        )

        self.assertEqual(
            plan.candidates[0].prompt,
            "Take @Element1 as Mother Bird, @Element2 as Little Blue Bird. "
            "close-up: feeding her chick a worm",
        )


class TestKlingDurationForWordCount(unittest.TestCase):
    def test_stays_at_5_within_budget(self):
        self.assertEqual(asset_generator._kling_duration_for_word_count(11), "5")

    def test_rounds_up_to_10_over_budget(self):
        self.assertEqual(asset_generator._kling_duration_for_word_count(12), "10")

    def test_zero_words_stays_at_5(self):
        self.assertEqual(asset_generator._kling_duration_for_word_count(0), "5")


if __name__ == "__main__":
    unittest.main()
