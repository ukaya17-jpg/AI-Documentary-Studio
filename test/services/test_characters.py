import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import characters


class TestGetCharacterReference(unittest.TestCase):
    """"Çoklu Karakter Sistemi" planı (kullanıcı onaylı): her karakterin
    front/three_quarter/back.jpg dosyaları gerçekten diskte var ve gerçek
    base64 data URI'lere çözülüyor -- CharacterReference.frontal_image_url/
    reference_image_urls fal.ai'ye giden GERÇEK alanlar, yerel dosya yolu
    OLAMAZ (bkz. docs/character-consistency-research.md'deki kanıtlanmış
    yöntem).
    """

    def test_all_seven_registered_characters_resolve_to_real_data_uris(self):
        for slug in characters._CHARACTER_SLUGS:
            ref = characters.get_character_reference(slug)
            self.assertTrue(ref.name)
            self.assertTrue(ref.frontal_image_url.startswith("data:image/jpeg;base64,"))
            self.assertEqual(len(ref.reference_image_urls), 2)
            for url in ref.reference_image_urls:
                self.assertTrue(url.startswith("data:image/jpeg;base64,"))

    def test_bao_reference_name_matches_registry(self):
        ref = characters.get_character_reference("bao")
        self.assertEqual(ref.name, "Bao")

    def test_unknown_slug_raises(self):
        with self.assertRaises(KeyError):
            characters.get_character_reference("nonexistent")


class TestResolveCharacterSelection(unittest.TestCase):
    def test_none_value_returns_empty_list(self):
        self.assertEqual(characters.resolve_character_selection(characters.NO_CHARACTER), [])

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(characters.resolve_character_selection(""), [])

    def test_unknown_value_returns_empty_list(self):
        # Bilinmeyen bir session_state değeri (ör. bozuk/eski veri) --
        # çökmemeli, sessizce "karaktersiz" davranmalı.
        self.assertEqual(characters.resolve_character_selection("does_not_exist"), [])

    def test_single_character_slug_returns_one_reference(self):
        refs = characters.resolve_character_selection("bao")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].name, "Bao")

    def test_pair_key_returns_two_references_in_element_order(self):
        refs = characters.resolve_character_selection("mother_and_baby")
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0].name, "Mother Bird")
        self.assertEqual(refs[1].name, "Little Blue Bird")

    def test_all_registered_slugs_are_individually_resolvable(self):
        for slug in characters._CHARACTER_SLUGS:
            refs = characters.resolve_character_selection(slug)
            self.assertEqual(len(refs), 1)


class TestCharacterVoiceName(unittest.TestCase):
    """"Karakter Sesi" planı (kullanıcı onaylı, Seçenek A): her karakterin
    sabit, gerçek ElevenLabs voice_id'sine (production'ın gerçek hesap
    kataloğundan, uydurma değil) sahip olması + 7 karakterin 7'sinin de
    birbirinden FARKLI bir sesi olması.
    """

    def test_all_seven_characters_have_a_real_elevenlabs_voice_name(self):
        for slug in characters._CHARACTER_SLUGS:
            voice_name = characters.get_character_voice_name(slug)
            self.assertTrue(voice_name.startswith("elevenlabs:"), f"{slug}: {voice_name!r}")
            # format: elevenlabs:<voice_id>:<display name>
            self.assertEqual(len(voice_name.split(":")), 3, f"{slug}: {voice_name!r}")

    def test_all_seven_voice_names_are_pairwise_distinct(self):
        voice_names = [characters.get_character_voice_name(slug) for slug in characters._CHARACTER_SLUGS]
        self.assertEqual(len(voice_names), len(set(voice_names)))

    def test_unknown_slug_raises(self):
        with self.assertRaises(KeyError):
            characters.get_character_voice_name("nonexistent")

    def test_get_voice_name_for_character_reference_matches_registry(self):
        for slug in characters._CHARACTER_SLUGS:
            ref = characters.get_character_reference(slug)
            expected = characters.get_character_voice_name(slug)
            self.assertEqual(characters.get_voice_name_for_character_reference(ref), expected)

    def test_get_voice_name_for_unregistered_character_reference_returns_empty_string(self):
        from app.models.character import CharacterReference

        unknown = CharacterReference(name="Nobody", frontal_image_url="data:image/jpeg;base64,x")
        self.assertEqual(characters.get_voice_name_for_character_reference(unknown), "")


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


if __name__ == "__main__":
    unittest.main()
