import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import characters


class TestEmptyCharacterRegistry(unittest.TestCase):
    """Registry temizligi (kullanici onayli): onceki 7 karakter kaldirildi,
    _CHARACTER_SLUGS/CHARACTER_PAIRS su an kasitli olarak bos -- kullanici
    Google Flow'da tasarladigi yeni karakterleriyle sifirdan dolduracak. Bu
    testler artik "7 karakter" degil, bos registry'nin ve mekanizmanin
    kendisinin (yeni karakter eklendiginde hala dogru calisacaginin)
    davranisini dogruluyor.
    """

    def test_registry_is_currently_empty(self):
        self.assertEqual(characters._CHARACTER_SLUGS, {})
        self.assertEqual(characters.CHARACTER_PAIRS, {})

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
        for legacy_slug in (
            "bao", "luna", "riko", "finn", "wise_owl",
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


if __name__ == "__main__":
    unittest.main()
