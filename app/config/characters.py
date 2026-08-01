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

# slug -> (display name, folder name under resource/characters/). The
# display name is only used to build the "@ElementN as <name>" prompt
# prefix (see asset_generator.build_asset_plan) -- never sent to the API.
_CHARACTER_SLUGS: dict[str, tuple[str, str]] = {
    "bao": ("Bao", "bao"),
    "luna": ("Luna", "luna"),
    "riko": ("Riko", "riko"),
    "finn": ("Finn", "finn"),
    "wise_owl": ("Wise Owl", "wise_owl"),
    "little_blue_bird": ("Little Blue Bird", "little_blue_bird"),
    "mother_bird": ("Mother Bird", "mother_bird"),
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
    name, folder = _CHARACTER_SLUGS[slug]
    base = utils.resource_dir(f"characters/{folder}")
    return CharacterReference(
        name=name,
        frontal_image_url=_data_uri(f"{base}/front.jpg"),
        reference_image_urls=[
            _data_uri(f"{base}/three_quarter.jpg"),
            _data_uri(f"{base}/back.jpg"),
        ],
    )


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
