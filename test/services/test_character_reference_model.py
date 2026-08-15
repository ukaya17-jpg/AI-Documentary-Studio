import base64
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image
from pydantic import ValidationError

from app.models.character import CharacterReference


def _data_uri(width: int, height: int) -> str:
    im = Image.new("RGB", (width, height), (128, 128, 128))
    buf = io.BytesIO()
    im.save(buf, "JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


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


class TestCharacterReferenceRejectsImagesFalAiWouldReject(unittest.TestCase):
    """İKİNCİ PRODÜKSİYON HATASI (kullanıcı bildirdi, 2026-08-15): ilk 422
    dalgasını (yukarıdaki sınıf) düzelttikten SONRA bile, Luna/Professor
    Nova'nın 275x768 -> 320x894 büyütülmüş (aynı oranı koruyan) görselleri
    fal.ai'nin AYRI bir kuralını ("aspect ratio between 0.4 and 2.5")
    ihlal etmeye devam etti -- boyut yeterliydi ama oran değildi. Bu
    testler, CharacterReference'ın artık HER İKİ kuralı da inşa anında
    (fal.ai'ye pahalı bir istek göndermeden ÖNCE) kilitlediğini doğrular.
    """

    def test_image_smaller_than_300x300_is_rejected(self):
        with self.assertRaises(ValidationError):
            CharacterReference(name="X", frontal_image_url=_data_uri(275, 768))

    def test_image_with_aspect_ratio_outside_0_4_to_2_5_is_rejected(self):
        # 320x894 -- yeterince büyük (>=300x300) ama oranı (0.358) çok dar.
        with self.assertRaises(ValidationError):
            CharacterReference(name="X", frontal_image_url=_data_uri(320, 894))

    def test_valid_dimensions_and_aspect_ratio_are_accepted(self):
        ref = CharacterReference(name="X", frontal_image_url=_data_uri(344, 768))
        self.assertEqual(ref.reference_image_urls, [ref.frontal_image_url])

    def test_non_data_uri_urls_are_not_inspected(self):
        # Uzak bir http(s) URL -- ağ çağrısı yapmadan boyut ölçülemez,
        # bu yüzden kontrol sessizce atlanmalı (reddetmemeli).
        ref = CharacterReference(name="X", frontal_image_url="https://example.com/x.jpg")
        self.assertEqual(ref.frontal_image_url, "https://example.com/x.jpg")


if __name__ == "__main__":
    unittest.main()
