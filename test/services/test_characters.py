import sys
import typing
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import characters


class TestNewFiveCharacterRegistry(unittest.TestCase):
    """"Yeni 5 Karakter" seti (kullanıcı onaylı, Google Flow'da tasarlandı):
    Professor Nova, Robo, Luna, Atom, Dino -- her biri gerçek voice_id'lerle
    (kullanıcının paylaştığı ElevenLabs hesap kütüphanesinden) kayıtlı.
    """

    EXPECTED_SLUGS: typing.ClassVar[set[str]] = {"professor_nova", "robo", "luna", "atom", "dino"}

    def test_all_five_slugs_are_registered(self):
        self.assertEqual(set(characters._CHARACTER_SLUGS), self.EXPECTED_SLUGS)

    def test_each_character_reference_loads_real_images(self):
        for slug in self.EXPECTED_SLUGS:
            ref = characters.get_character_reference(slug)
            self.assertTrue(ref.frontal_image_url.startswith("data:image/jpeg;base64,"))
            self.assertEqual(len(ref.reference_image_urls), 2)
            for uri in ref.reference_image_urls:
                self.assertTrue(uri.startswith("data:image/jpeg;base64,"))

    def test_each_character_has_a_distinct_elevenlabs_voice(self):
        voices = [characters.get_character_voice_name(slug) for slug in self.EXPECTED_SLUGS]
        self.assertEqual(len(voices), len(set(voices)), "voice_name'ler benzersiz olmalı")
        for voice in voices:
            self.assertTrue(voice.startswith("elevenlabs:"))

    def test_resolve_character_selection_returns_the_right_single_character(self):
        for slug in self.EXPECTED_SLUGS:
            refs = characters.resolve_character_selection(slug)
            self.assertEqual(len(refs), 1)
            expected_name, _folder, _voice = characters._CHARACTER_SLUGS[slug]
            self.assertEqual(refs[0].name, expected_name)

    def test_get_voice_name_for_character_reference_round_trips(self):
        for slug in self.EXPECTED_SLUGS:
            ref = characters.get_character_reference(slug)
            expected_voice = characters.get_character_voice_name(slug)
            self.assertEqual(
                characters.get_voice_name_for_character_reference(ref), expected_voice
            )


class TestEmptyCharacterRegistry(unittest.TestCase):
    """Registry artık boş DEĞİL (5 karakter var, bkz.
    TestNewFiveCharacterRegistry) -- bu sınıf yalnızca "bilinmeyen slug"
    davranışını (KeyError) doğruluyor.
    """

    def test_unknown_slug_raises(self):
        with self.assertRaises(KeyError):
            characters.get_character_reference("nonexistent")

    def test_unknown_voice_slug_raises(self):
        with self.assertRaises(KeyError):
            characters.get_character_voice_name("nonexistent")


class TestResolveCharacterSelection(unittest.TestCase):
    def test_none_value_returns_empty_list(self):
        self.assertEqual(characters.resolve_character_selection(characters.NO_CHARACTER), [])

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(characters.resolve_character_selection(""), [])

    def test_unknown_value_returns_empty_list(self):
        # Bilinmeyen bir session_state degeri (or. bozuk/eski veri, ya da
        # kaldirilmis eski bir karakter slug'i) -- cokmemeli, sessizce
        # "karaktersiz" davranmali.
        self.assertEqual(characters.resolve_character_selection("does_not_exist"), [])

    def test_removed_legacy_slugs_resolve_to_empty_list(self):
        # Eskiden kayitliydi, artik degil -- sessizce "karaktersiz"
        # davranmali, KeyError FIRLATMAMALI (webui dogrudan bu fonksiyonu
        # cagiriyor, session_state'te eski bir secim kalmis olabilir).
        # NOT: "luna" burada YOK -- o slug artik YENI bir karaktere (Google
        # Flow'daki astronot Luna) atanmis durumda, eski tavsan Luna ile
        # ILGISIZ. resolve_character_selection("luna") artik gercek bir
        # sonuc donduruyor, bkz. TestNewFiveCharacterRegistry.
        for legacy_slug in (
            "bao", "riko", "finn", "wise_owl",
            "little_blue_bird", "mother_bird", "mother_and_baby",
        ):
            self.assertEqual(characters.resolve_character_selection(legacy_slug), [])


class TestCharacterPairsReferenceValidSlugs(unittest.TestCase):
    def test_every_pair_member_is_a_registered_character(self):
        for pair_key, slugs in characters.CHARACTER_PAIRS.items():
            for slug in slugs:
                self.assertIn(
                    slug,
                    characters._CHARACTER_SLUGS,
                    f"pair {pair_key!r} references unknown character slug {slug!r}",
                )

    def test_no_pair_is_empty_or_a_single_character(self):
        for pair_key, slugs in characters.CHARACTER_PAIRS.items():
            self.assertGreaterEqual(len(slugs), 2, f"pair {pair_key!r} has fewer than 2 members")


class TestGetVoiceNameForCharacterReference(unittest.TestCase):
    def test_get_voice_name_for_unregistered_character_reference_returns_empty_string(self):
        from app.models.character import CharacterReference

        unknown = CharacterReference(name="Nobody", frontal_image_url="data:image/jpeg;base64,x")
        self.assertEqual(characters.get_voice_name_for_character_reference(unknown), "")


class TestAutoCharacterConstant(unittest.TestCase):
    """"Sahne Bazlı Otomatik Kadrolama" planı (kullanıcı onaylı): bkz.
    test_locations.py'deki TestAutoLocationConstant'ın aynı gerekçesi.
    """

    def test_auto_character_is_not_a_registered_slug(self):
        self.assertNotIn(characters.AUTO_CHARACTER, characters._CHARACTER_SLUGS)

    def test_auto_character_differs_from_no_character(self):
        self.assertNotEqual(characters.AUTO_CHARACTER, characters.NO_CHARACTER)

    def test_resolve_character_selection_of_auto_returns_empty_list(self):
        self.assertEqual(characters.resolve_character_selection(characters.AUTO_CHARACTER), [])

    def test_character_descriptions_for_casting_keys_match_registry(self):
        self.assertEqual(
            set(characters.character_descriptions_for_casting()), set(characters._CHARACTER_SLUGS)
        )


if __name__ == "__main__":
    unittest.main()
