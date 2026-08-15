import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.character import CharacterReference


class TestCharacterReferenceAlwaysHasAtLeastOneReferenceImage(unittest.TestCase):
    """PRODUKSİYON HATASI (kullanıcı bildirdi, 2026-08-15): fal.ai'nin
    gerçek Kling O1 şeması `reference_image_urls` için "array of 1-3
    additional images" istiyor (bkz. docs/character-consistency-
    research.md) -- boş liste GEÇERSİZ, fal.ai'yi 422 Unprocessable
    Entity ile reddettiriyordu. Tek-açı (front.jpg only) mekanlar
    reference_image_urls'i boş bırakıyordu -- bu, karakter/mekan içeren
    HER sahnenin başarısız olmasına yol açtı (10 sahnelik bir üretimde
    9'u). Bu testler, CharacterReference'ın bu durumu ARTIK asla
    üretmediğini kilitliyor.
    """

    def test_omitted_reference_image_urls_defaults_to_frontal_image(self):
        ref = CharacterReference(name="X", frontal_image_url="data:image/jpeg;base64,front")
        self.assertEqual(ref.reference_image_urls, ["data:image/jpeg;base64,front"])

    def test_explicitly_empty_list_also_falls_back_to_frontal_image(self):
        # Field(default_factory=list) İLE elle geçirilen [] ARASINDAKİ
        # fark önemli değil -- ikisi de aynı sonuca varmalı (pydantic v2
        # field_validator'ın validate_default olmadan defaultlarda hiç
        # çalışmama tuzağına düşülmediğini de dolaylı olarak doğruluyor).
        ref = CharacterReference(
            name="X", frontal_image_url="data:image/jpeg;base64,front", reference_image_urls=[]
        )
        self.assertEqual(ref.reference_image_urls, ["data:image/jpeg;base64,front"])

    def test_non_empty_reference_image_urls_is_preserved_unchanged(self):
        # Gerçek ek açılar (karakterlerin 3'lü seti gibi) ASLA değiştirilmemeli.
        ref = CharacterReference(
            name="X",
            frontal_image_url="data:image/jpeg;base64,front",
            reference_image_urls=["data:image/jpeg;base64,threeq", "data:image/jpeg;base64,back"],
        )
        self.assertEqual(
            ref.reference_image_urls,
            ["data:image/jpeg;base64,threeq", "data:image/jpeg;base64,back"],
        )

    def test_model_dump_never_contains_an_empty_reference_image_urls_list(self):
        # fal.ai'ye giden GERÇEK payload (ai_video_generator.py'nin
        # character_elements = [ref.model_dump() for ref in ...] yaptığı
        # tam biçim) hiçbir zaman boş liste İÇERMEMELİ.
        ref = CharacterReference(name="X", frontal_image_url="data:image/jpeg;base64,front")
        dumped = ref.model_dump()
        self.assertTrue(len(dumped["reference_image_urls"]) >= 1)


if __name__ == "__main__":
    unittest.main()
