"""Registry of known recurring characters for character-consistent AI video
generation (Kling O1 Reference-to-Video -- see
docs/character-consistency-research.md).

Each character's reference images live at
resource/characters/<slug>/{front,three_quarter,back}.jpg (cropped once,
locally, from a single 3-view triptych -- see PROGRESS.md's "Bao" and
"Coklu Karakter Sistemi" entries). `CharacterReference.frontal_image_url`/
`reference_image_urls` must hold something fal.ai's API can fetch (a real
URL or a data URI) -- NOT a local filesystem path -- so `get_character_
reference()` reads each file and inlines it as a base64 data URI, lazily
(only for characters actually selected), mirroring the exact technique
already proven in the real Kling O1 test.

Registry temizligi + yeni set (kullanici onayli): onceki 7 karakter (Bao,
Luna, Riko, Finn, Wise Owl, Little Blue Bird, Mother Bird) kaldirildiktan
sonra, kullanicinin Google Flow'da tasarladigi YENI 5 karakter (Professor
Nova, Robo, Luna, Atom, Dino) eklendi -- eskiyle isim cakismasi olan tek
karakter "Luna" (astronot/bilim insani), eski "Luna" (tavsan) ile ILGISIZ,
tamamen farkli bir tasarim/gorsel. Bu dosyanin altyapisi (CharacterReference,
resolve_character_selection, get_character_reference, vb.) hic degismedi --
yeni bir karakter eklemek icin tek yapilmasi gereken _CHARACTER_SLUGS'a bir
satir eklemek ve resource/characters/<slug>/{front,three_quarter,back}.jpg
dosyalarini yerlestirmek. Ses secimi icin: voice.get_elevenlabs_voices()
icindeki gercek, favorilenmis hesap katalogundan, karakterin kisiligine
uygun perde/enerjiyle secilmeli.
"""

import base64

from app.models.character import CharacterReference
from app.utils import utils

# slug -> (display name, folder name under resource/characters/, ElevenLabs
# voice_name). Display name yalnizca "@ElementN as <n>" prompt onekini
# olusturmak icin kullanilir (bkz. asset_generator.build_asset_plan) -- API'ye
# gonderilmez.
#
# "Yeni 5 Karakter" seti (kullanici onayli, Google Flow'da tasarlandi): her
# voice_name, kullanicinin PAYLASTIGI gercek ElevenLabs hesap kutuphanesinden
# (voice_id + tam ad) birebir alindi -- uydurma bir voice_id DEGIL. Karakter
# <-> ses eslesmesi dogrudan kullanicinin kendi tercihi:
#   Professor Nova (bilim insani) -> Eyyüp Okan: "Dynamic and Authentic"
#   Robo (minik, sevimli robot)   -> Gözde
#   Luna (astronot/bilim insani)  -> Nazlı Yeni: "Friendly, Sympathetic"
#   Atom (AI küp karakter)        -> Mark: "Cartoonish, Funny and Cheerful"
#   Dino (yavru dinozor)          -> Alican: "Youthful, Encouraging"
# 5 ses birbirinden FARKLI voice_id -- hicbiri paylasilmiyor.
_CHARACTER_SLUGS: dict[str, tuple[str, str, str]] = {
    "professor_nova": (
        "Professor Nova", "professor_nova",
        "elevenlabs:sqN4QwtcnanCCWx6TTYj:Eyyup Okan - Dynamic and Authentic",
    ),
    "robo": (
        "Robo", "robo",
        "elevenlabs:rtnDjO8siSxeTEeTVczO:Gözde",
    ),
    "luna": (
        "Luna", "luna",
        "elevenlabs:o9DOmAyPjfFu8AfoFAnM:Nazlı Yeni - Friendly, Sympathetic",
    ),
    "atom": (
        "Atom", "atom",
        "elevenlabs:DUnzBkwtjRWXPr6wRbmL:Mark - Cartoonish, Funny and Cheerful",
    ),
    "dino": (
        "Dino", "dino",
        "elevenlabs:wRfRD9nLN4QfAuuFAyqY:Alican - Youthful, Encouraging",
    ),
}

# A composite ("pair") selection resolves to multiple individual character
# slugs, in @ElementN order -- e.g. {"mother_and_baby": ["mother_bird",
# "little_blue_bird"]}. Yeni karakterler eklenince, birlikte sahne
# paylasmasi gereken ciftler burada tanimlanabilir. Su an bu 5 karakter icin
# tanimli bir cift YOK (YAGNI) -- ihtiyac olursa tek satirla eklenir.
CHARACTER_PAIRS: dict[str, list[str]] = {}

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
