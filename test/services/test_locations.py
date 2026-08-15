import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import locations


class TestTenLocationRegistry(unittest.TestCase):
    """"Mekan Sistemi" seti (kullanıcı onaylı, Google Flow'da tasarlandı):
    10 mekan, her biri gerçek 4K referans görselinden (tek açı) kayıtlı.
    """

    EXPECTED_SLUGS = {
        "professor_nova_lab", "kutuphane", "tarih_muzesi",
        "gelecek_teknoloji_lab", "gozlemevi", "uzay_kontrol_merkezi",
        "robot_atolyesi", "kimya_laboratuvari", "ai_inovasyon_lab",
        "dunya_cografya_odasi",
    }

    def test_all_ten_slugs_are_registered(self):
        self.assertEqual(set(locations._LOCATION_SLUGS), self.EXPECTED_SLUGS)

    def test_each_location_reference_loads_a_real_image(self):
        for slug in self.EXPECTED_SLUGS:
            ref = locations.get_location_reference(slug)
            self.assertTrue(ref.frontal_image_url.startswith("data:image/jpeg;base64,"))
            self.assertTrue(ref.name)

    def test_single_view_locations_fall_back_to_duplicated_frontal_image(self):
        # PRODÜKSİYON HATASI DÜZELTMESİ (kullanıcı bildirdi, 2026-08-15):
        # bu 10 mekan tek-açı (front.jpg only) yüklendi -- three_quarter/
        # back diskte yok. ESKİDEN bu, reference_image_urls'i BOŞ
        # bırakıyordu -- fal.ai'nin gerçek O1 şeması bunu KABUL ETMİYOR
        # ("array of 1-3", min 1), her sahnede 422 Unprocessable Entity'ye
        # yol açıyordu. Artık CharacterReference'ın kendi model_validator'ı
        # (bkz. app/models/character.py) boş kalan reference_image_urls'i
        # frontal_image_url ile dolduruyor -- burada SADECE o davranışın
        # mekan tarafında da gerçekten tetiklendiğini doğruluyoruz.
        for slug in self.EXPECTED_SLUGS:
            ref = locations.get_location_reference(slug)
            self.assertEqual(ref.reference_image_urls, [ref.frontal_image_url])

    def test_resolve_location_selection_returns_the_right_single_location(self):
        for slug in self.EXPECTED_SLUGS:
            refs = locations.resolve_location_selection(slug)
            self.assertEqual(len(refs), 1)
            expected_name, _folder = locations._LOCATION_SLUGS[slug]
            self.assertEqual(refs[0].name, expected_name)


class TestResolveLocationSelection(unittest.TestCase):
    def test_none_value_returns_empty_list(self):
        self.assertEqual(locations.resolve_location_selection(locations.NO_LOCATION), [])

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(locations.resolve_location_selection(""), [])

    def test_unknown_value_returns_empty_list(self):
        self.assertEqual(locations.resolve_location_selection("does_not_exist"), [])


class TestUnknownLocationSlugRaises(unittest.TestCase):
    def test_unknown_slug_raises(self):
        with self.assertRaises(KeyError):
            locations.get_location_reference("nonexistent")


class TestAutoLocationConstant(unittest.TestCase):
    """"Sahne Bazlı Otomatik Kadrolama" planı (kullanıcı onaylı):
    AUTO_LOCATION, NO_LOCATION'dan (ve gerçek slug'lardan) ayrı, kendine
    özgü bir sentinel -- default_pipeline._resolve_references_by_scene bu
    değere göre casting_generator'ı tetikliyor mu, tetiklemiyor mu karar
    veriyor.
    """

    def test_auto_location_is_not_a_registered_slug(self):
        self.assertNotIn(locations.AUTO_LOCATION, locations._LOCATION_SLUGS)

    def test_auto_location_differs_from_no_location(self):
        self.assertNotEqual(locations.AUTO_LOCATION, locations.NO_LOCATION)

    def test_resolve_location_selection_of_auto_returns_empty_list(self):
        # resolve_location_selection kendisi "auto"yu ÖZEL olarak
        # işlemiyor -- kayıtlı bir slug olmadığı için doğal olarak boş
        # liste dönüyor (default_pipeline, AUTO_LOCATION'ı ayrı bir
        # parametreden -- location_selection -- okuyup gerçek kadrolamayı
        # kendisi yapıyor, resolve_location_selection'dan DEĞİL).
        self.assertEqual(locations.resolve_location_selection(locations.AUTO_LOCATION), [])

    def test_location_descriptions_for_casting_keys_match_registry(self):
        self.assertEqual(
            set(locations.location_descriptions_for_casting()), set(locations._LOCATION_SLUGS)
        )


if __name__ == "__main__":
    unittest.main()
