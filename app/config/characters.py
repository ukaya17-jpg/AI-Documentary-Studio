"""Registry of known recurring characters for character-consistent AI video
generation (Kling O1 Reference-to-Video -- see
docs/character-consistency-research.md).

Each character's reference images live at
resource/characters/<slug>/{front,three_quarter,back}.jpg (cropped once,
locally, from a single 3-view triptych -- see PROGRESS.md's "Bao" and
"Çoklu Karakter Sistemi" entries). `CharacterReference.frontal_image_url`/
`reference_image_urls` must hold something fal.ai's API can fetch (a real
URL or a data URI) -- NOT a local filesystem path -- so `get_character_
reference()` reads each file and inlines it as a base64 data URI, lazily
(only for characters actually selected), mirroring the exact technique
already proven in the real Kling O1 test.
"""

import base64

from app.models.character import CharacterReference
from app.utils import utils

# slug -> (display name, folder name under resource/characters/, ElevenLabs
# voice_name). The display name is only used to build the "@ElementN as
# <name>" prompt prefix (see asset_generator.build_asset_plan) -- never
# sent to the API.
#
# "Karakter Sesi" planı (kullanıcı onaylı, Seçenek A): her voice_name,
# production config.toml'un GERÇEK varsayılan sağlayıcısı olan
# ElevenLabs'ın (Azure değil) gerçek, favorilenmiş hesap kataloğundan
# (voice.get_elevenlabs_voices(), 36 ses) seçildi -- uydurma bir voice_id
# DEĞİL. model_id "eleven_multilingual_v2" (config.toml) olduğu için
# hepsi Türkçe metni de doğal şekilde okuyabiliyor, sesin kendi
# "native dili" etiketinden bağımsız. Her ses, karakterin kişiliğine göre
# BİLİNÇLİ seçildi (perde/enerji farklılaştırması):
#   Bao (sakin, şefkatli panda) -> Burak Kal: "Rich, Reassuring and Warm"
#   Luna (yumuşak huylu tavşan) -> Nisa: "Encouraging, Friendly and Soft"
#   Riko (enerjik, maceraperest rakun) -> Tomris: "Live, Energetic and Friendly"
#   Finn (meraklı, kurnaz tilki) -> Callum: "Husky Trickster" (tilki=kurnaz motifiyle örtüşüyor)
#   Wise Owl (sakin, bilge) -> Bill: "Wise, Mature, Balanced" (etiketin kendisi "Wise")
#   Little Blue Bird (minik yavru civciv) -> Jessica: "Playful, Bright, Warm" (en genç/canlı doku)
#   Mother Bird (şefkatli anne) -> Sarah: "Mature, Reassuring, Confident" (anne figürüne uygun olgun ton)
# 7 ses birbirinden FARKLI voice_id -- hiçbiri paylaşılmıyor.
_CHARACTER_SLUGS: dict[str, tuple[str, str, str]] = {
    "bao": (
        "Bao", "bao",
        "elevenlabs:stvBE08BCYHZ97rCIwoZ:Burak Kal - Rich, Reassuring and Warm",
    ),
    "luna": (
        "Luna", "luna",
        "elevenlabs:bj1uMlYGikistcXNmFoh:Nisa - Encouraging, Friendly and Soft",
    ),
    "riko": (
        "Riko", "riko",
        "elevenlabs:bqaNYmxFgK1TN7CL95PZ:Tomris - Live, Energetic and Friendly",
    ),
    "finn": (
        "Finn", "finn",
        "elevenlabs:N2lVS1w4EtoT3dr4eOWO:Callum - Husky Trickster",
    ),
    "wise_owl": (
        "Wise Owl", "wise_owl",
        "elevenlabs:pqHfZKP75CvOlQylNhV4:Bill - Wise, Mature, Balanced",
    ),
    "little_blue_bird": (
        "Little Blue Bird", "little_blue_bird",
        "elevenlabs:cgSgspJ2msm6clMCkdW9:Jessica - Playful, Bright, Warm",
    ),
    "mother_bird": (
        "Mother Bird", "mother_bird",
        "elevenlabs:EXAVITQu4vr4xnSDxMaL:Sarah - Mature, Reassuring, Confident",
    ),
}

# A composite ("pair") selection resolves to multiple individual character
# slugs, in @ElementN order. "Çoklu Karakter Sistemi" planı (kullanıcı
# onaylı): bugün tek somut ihtiyaç bu ikili -- genel bir "N karakter seç"
# mekanizması BİLEREK kurulmuyor (YAGNI), yeni bir çift gerekirse buraya
# tek satır eklemek yeterli.
CHARACTER_PAIRS: dict[str, list[str]] = {
    "mother_and_baby": ["mother_bird", "little_blue_bird"],
}

NO_CHARACTER = "none"


def _data_uri(path: str) -> str:
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def get_character_reference(slug: str) -> CharacterReference:
    """Reads one character's 3 cropped reference images from disk and
    returns a CharacterReference with real data-URI image fields, ready to
    pass into run_pipeline(character_references=...).
    """
    name, folder, _voice_name = _CHARACTER_SLUGS[slug]
    base = utils.resource_dir(f"characters/{folder}")
    return CharacterReference(
        name=name,
        frontal_image_url=_data_uri(f"{base}/front.jpg"),
        reference_image_urls=[
            _data_uri(f"{base}/three_quarter.jpg"),
            _data_uri(f"{base}/back.jpg"),
        ],
    )


def get_character_voice_name(slug: str) -> str:
    """The character's fixed ElevenLabs voice_name (see the "Karakter
    Sesi" comment above _CHARACTER_SLUGS for how/why each was picked).
    Deliberately NOT a field on CharacterReference itself -- that model's
    model_dump() is sent directly to fal.ai as an `elements[]` entry (see
    ai_video_generator.py), and fal.ai's schema has no voice concept --
    adding it there would leak an unexpected field into that real API
    payload. This stays a separate, audio-only lookup.
    """
    _name, _folder, voice_name = _CHARACTER_SLUGS[slug]
    return voice_name


def get_voice_name_for_character_reference(reference: CharacterReference) -> str:
    """Reverse lookup: given an already-resolved CharacterReference (e.g.
    from resolve_character_selection()), finds its registered voice_name
    by matching on `.name` -- avoids threading the raw slug string through
    the pipeline as a second parameter alongside character_references.
    Returns "" if no registry entry matches (e.g. a CharacterReference
    built outside this registry, such as in a test).
    """
    for name, _folder, voice_name in _CHARACTER_SLUGS.values():
        if name == reference.name:
            return voice_name
    return ""


def resolve_character_selection(selection: str) -> list[CharacterReference]:
    """`selection` is a raw value from the webui character card grid:
    NO_CHARACTER ("none"), a single slug (a _CHARACTER_SLUGS key), or a
    pair key (a CHARACTER_PAIRS key). Returns the ordered list of
    CharacterReference objects -- empty for NO_CHARACTER/unknown values,
    one entry for a single character, N entries (in @ElementN order) for
    a pair.
    """
    if not selection or selection == NO_CHARACTER:
        return []
    if selection in CHARACTER_PAIRS:
        return [get_character_reference(slug) for slug in CHARACTER_PAIRS[selection]]
    if selection in _CHARACTER_SLUGS:
        return [get_character_reference(selection)]
    return []
