import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.departments.growth import seo_generator
from app.models.scene import Scene, ScenePlan
from app.models.script import Script


def _scene_plan():
    return ScenePlan(
        scenes=[
            Scene(index=0, title="Origins", duration_seconds=5.0),
            Scene(index=1, title="Decline", duration_seconds=65.0),
            Scene(index=2, title="Fall", duration_seconds=8.0),
        ]
    )


class TestGenerateChapters(unittest.TestCase):
    def test_computes_cumulative_mm_ss_markers(self):
        chapters = seo_generator.generate_chapters(_scene_plan())
        self.assertEqual(chapters, ["0:00 Origins", "0:05 Decline", "1:10 Fall"])

    def test_returns_empty_list_for_none(self):
        self.assertEqual(seo_generator.generate_chapters(None), [])

    def test_returns_empty_list_for_empty_scene_plan(self):
        self.assertEqual(seo_generator.generate_chapters(ScenePlan(scenes=[])), [])


class TestBuildEngagementPrompt(unittest.TestCase):
    def test_asks_for_title_variants_and_keywords(self):
        # GÖREV 2 (SEO Engine genişletmesi): bu talimatların prompt'ta
        # gerçekten var olduğunu kilitliyor, sadece parse edilmesini değil.
        prompt = seo_generator.build_engagement_prompt(
            "The Fall of Rome", Script(full_text="Rome fell.")
        )
        self.assertIn("title_variants", prompt)
        self.assertIn("keywords", prompt)
        self.assertIn("exactly 2 alternative titles", prompt)
        self.assertIn("no \"#\" prefix", prompt)

    def test_omits_existing_title_context_when_not_given(self):
        prompt = seo_generator.build_engagement_prompt(
            "The Fall of Rome", Script(full_text="Rome fell.")
        )
        self.assertNotIn("main title is already", prompt)

    def test_includes_existing_title_context_when_given(self):
        # GÖREV 2 sonrası bulunan gerçek bir kalite sorunu: title ve
        # title_variants iki ayrı LLM çağrısından geldiği için, ikinci
        # çağrı birincinin sonucunu bilmeden aynı başlığı üretebiliyordu
        # (gerçek API doğrulamasında gözlemlendi). Bu context olmadan bu
        # test de geçerdi ama regresyonu hiç yakalamazdı -- prompt'un
        # gerçekten ana başlığı içerdiğini kilitliyor.
        prompt = seo_generator.build_engagement_prompt(
            "The Fall of Rome",
            Script(full_text="Rome fell."),
            existing_title="Why Rome Really Fell",
        )
        self.assertIn('"Why Rome Really Fell"', prompt)
        self.assertIn("genuinely different from the main title", prompt)

    def test_omits_verified_facts_block_when_no_key_facts_given(self):
        prompt = seo_generator.build_engagement_prompt(
            "The Fall of Rome", Script(full_text="Rome fell.")
        )
        self.assertNotIn("Verified facts", prompt)

    def test_includes_verified_facts_and_time_scale_instruction_when_given(self):
        # Truva prod bugı: script sayısal bir zaman ölçeği vermiyordu, SEO da
        # "yüzyıllar" diye uydurdu -- oysa research_plan.key_facts doğru
        # ölçeği ("~3.000 yıl") zaten biliyordu. Bu test, o fact buraya
        # verildiğinde prompt'ta gerçekten göründüğünü ve model'e ölçek
        # tutarlılığı talimatı verildiğini kilitliyor.
        prompt = seo_generator.build_engagement_prompt(
            "Troy",
            Script(full_text="Layers of time rise here."),
            key_facts=[
                "The site has roughly 3,000 years of continuous settlement.",
                "  ",
                "",
            ],
        )
        self.assertIn("Verified facts", prompt)
        self.assertIn(
            "roughly 3,000 years of continuous settlement", prompt
        )
        self.assertIn("century", prompt)
        self.assertIn("millennium", prompt)
        # boş/whitespace fact'ler filtrelenmeli
        self.assertNotIn("- \n", prompt)


class TestGenerateEngagementMetadata(unittest.TestCase):
    @patch("app.departments.growth.seo_generator.generate_json")
    def test_returns_parsed_fields(self, mock_generate_json):
        mock_generate_json.return_value = {
            "end_screen_suggestion": "Ask viewers to subscribe for more history content.",
            "pinned_comment": "What do you think caused Rome's fall the most?",
            "title_variants": ["Why Rome Really Fell", "The Empire's Final Days"],
            "keywords": ["roman empire", "fall of rome", "ancient history"],
        }
        result = seo_generator.generate_engagement_metadata(
            "The Fall of Rome", Script(full_text="Rome fell.")
        )
        self.assertEqual(
            result["end_screen_suggestion"],
            "Ask viewers to subscribe for more history content.",
        )
        self.assertEqual(
            result["pinned_comment"], "What do you think caused Rome's fall the most?"
        )
        self.assertEqual(
            result["title_variants"], ["Why Rome Really Fell", "The Empire's Final Days"]
        )
        self.assertEqual(
            result["keywords"], ["roman empire", "fall of rome", "ancient history"]
        )

    @patch("app.departments.growth.seo_generator.generate_json")
    def test_drops_blank_title_variants_and_keywords(self, mock_generate_json):
        mock_generate_json.return_value = {
            "end_screen_suggestion": "Subscribe for more.",
            "pinned_comment": "What do you think?",
            "title_variants": ["A Real Title", "  ", ""],
            "keywords": ["real keyword", "", "   "],
        }
        result = seo_generator.generate_engagement_metadata(
            "The Fall of Rome", Script(full_text="Rome fell.")
        )
        self.assertEqual(result["title_variants"], ["A Real Title"])
        self.assertEqual(result["keywords"], ["real keyword"])

    @patch("app.departments.growth.seo_generator.generate_json")
    def test_returns_empty_strings_on_failure(self, mock_generate_json):
        mock_generate_json.side_effect = ValueError("mock LLM failure")
        result = seo_generator.generate_engagement_metadata(
            "The Fall of Rome", Script(full_text="Rome fell.")
        )
        self.assertEqual(
            result,
            {
                "end_screen_suggestion": "",
                "pinned_comment": "",
                "title_variants": [],
                "keywords": [],
            },
        )


class TestGenerateSeoMetadata(unittest.TestCase):
    @patch("app.departments.growth.seo_generator.generate_json")
    @patch("app.departments.growth.seo_generator.llm.generate_social_metadata")
    def test_maps_social_metadata_result_to_seo_metadata(
        self, mock_generate_social_metadata, mock_generate_json
    ):
        mock_generate_social_metadata.return_value = {
            "title": "The Fall of Rome",
            "caption": "How the mightiest empire in history collapsed.",
            "hashtags": ["#history", "#rome"],
        }
        mock_generate_json.return_value = {
            "end_screen_suggestion": "Subscribe for more.",
            "pinned_comment": "What do you think?",
            "title_variants": ["Why Rome Really Fell", "The Empire's Final Days"],
            "keywords": ["roman empire", "fall of rome"],
        }
        script = Script(full_text="Rome fell in 476 AD.")
        seo = seo_generator.generate_seo_metadata(
            "The Fall of Rome", script, language="en", scene_plan=_scene_plan()
        )

        self.assertEqual(seo.title, "The Fall of Rome")
        self.assertEqual(seo.description, "How the mightiest empire in history collapsed.")
        self.assertEqual(seo.hashtags, ["#history", "#rome"])
        self.assertEqual(seo.chapters, ["0:00 Origins", "0:05 Decline", "1:10 Fall"])
        self.assertEqual(seo.end_screen_suggestion, "Subscribe for more.")
        self.assertEqual(seo.pinned_comment, "What do you think?")
        self.assertEqual(
            seo.title_variants, ["Why Rome Really Fell", "The Empire's Final Days"]
        )
        self.assertEqual(seo.keywords, ["roman empire", "fall of rome"])
        mock_generate_social_metadata.assert_called_once_with(
            video_subject="The Fall of Rome",
            video_script="Rome fell in 476 AD.",
            language="en",
            platform="youtube_shorts",
            key_facts=None,
        )
        # generate_engagement_metadata'ya gönderilen prompt'un, social_
        # metadata'nın ürettiği başlığı context olarak içerdiğini doğrula --
        # bu, title_variants'ın ana başlıkla aynı çıkma riskini azaltan
        # düzeltmenin gerçekten uçtan uca bağlandığını kanıtlıyor.
        engagement_prompt = mock_generate_json.call_args[0][0]
        self.assertIn('main title is already: "The Fall of Rome"', engagement_prompt)

    @patch("app.departments.growth.seo_generator.generate_json")
    @patch("app.departments.growth.seo_generator.llm.generate_social_metadata")
    def test_forwards_key_facts_to_both_social_metadata_and_engagement_calls(
        self, mock_generate_social_metadata, mock_generate_json
    ):
        # Yüzyıl/binyıl grounding düzeltmesi: araştırma aşamasında doğrulanmış
        # key_facts, hem caption/title'ı üreten paylaşılan
        # generate_social_metadata çağrısına HEM DE title_variants/keywords'ü
        # üreten generate_engagement_metadata çağrısına ulaşmalı -- ikisi de
        # aynı script'ten (kendi başına sayısal bir zaman ölçeği vermeyebilir)
        # bağımsız olarak yanlış bir ölçek uydurabilir.
        mock_generate_social_metadata.return_value = {
            "title": "T", "caption": "C", "hashtags": []
        }
        mock_generate_json.return_value = {}
        facts = ["The site has roughly 3,000 years of continuous settlement."]
        seo_generator.generate_seo_metadata(
            "Troy", Script(full_text="Layers of time rise here."), key_facts=facts
        )

        mock_generate_social_metadata.assert_called_once_with(
            video_subject="Troy",
            video_script="Layers of time rise here.",
            language="auto",
            platform="youtube_shorts",
            key_facts=facts,
        )
        engagement_prompt = mock_generate_json.call_args[0][0]
        self.assertIn("roughly 3,000 years of continuous settlement", engagement_prompt)

    @patch("app.departments.growth.seo_generator.generate_json")
    @patch("app.departments.growth.seo_generator.llm.generate_social_metadata")
    def test_empty_chapters_when_no_scene_plan_given(
        self, mock_generate_social_metadata, mock_generate_json
    ):
        mock_generate_social_metadata.return_value = {
            "title": "T", "caption": "C", "hashtags": []
        }
        mock_generate_json.return_value = {}
        seo = seo_generator.generate_seo_metadata("T", Script(full_text="text"))
        self.assertEqual(seo.chapters, [])


if __name__ == "__main__":
    unittest.main()
