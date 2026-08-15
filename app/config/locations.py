"""Registry of known recurring locations for scene-consistent AI video
generation -- the exact same Kling O1 Reference-to-Video mechanism as
app.config.characters (see docs/character-consistency-research.md), just
applied to a *place* instead of a *character*. `CharacterReference` is
reused as-is (it maps 1:1 onto fal.ai's `elements[]` entry shape and has no
character-specific field) -- a location is simply another named reference
element.

Each location's reference image lives at
resource/locations/<slug>/front.jpg -- a SINGLE view (unlike characters'
front/three_quarter/back triptych), since these were user-supplied as one
4K still per location, not a multi-angle turnaround sheet. `front.jpg` is
the only required file; if `three_quarter.jpg`/`back.jpg` are later added
on disk for a given slug, get_location_reference() picks them up
automatically (same optional-extra-views pattern), no code change needed.

"Mekan Sistemi" (kullanıcı onaylı, Google Flow'da tasarlandı, 10 mekan):
Kullanıcının yüklediği dosya adları içerikle UYUŞMUYORDU (muhtemelen Flow'un
toplu indirmesinde bir eşleşme hatası) -- bu registry, dosya adlarına değil,
her görselin GERÇEK içeriğine bakılarak elle doğrulanan slug'larla kuruldu.
Kullanıcı onayladı.

Karakter + mekan aynı sahnede BİRLİKTE seçilebilir -- ama bu ikisi ASLA aynı
Python listesinde karıştırılmaz: default_pipeline.run_pipeline() ikisini
SADECE prompt/API-payload oluşturma noktasında (asset_generator,
ai_video_generator) birleştirir; audio_renderer'a giden character_references
her zaman SADECE karakterleri içerir. Sebep: audio_renderer'ın "Karakter
Sesi" mekanizması `len(character_references) == 1` kontrolüne dayanıyor --
bir mekan da listeye karışsaydı bu sayı 2 olur, karakterin sesi SESSİZCE
devre dışı kalırdı. Bu ayrım BİLİNÇLİ ve regresyon karşıtı.
"""

import base64

from app.models.character import CharacterReference
from app.utils import utils

# slug -> (display name, folder name under resource/locations/). Display
# name yalnizca "@ElementN as <n>" prompt onekini olusturmak icin kullanilir
# (characters.py ile ayni desen) -- API'ye gonderilmez. Mekanlarin sesi
# olmadigi icin characters._CHARACTER_SLUGS'daki 3'lu tuple yerine burada
# 2'li tuple yeterli.
_LOCATION_SLUGS: dict[str, tuple[str, str]] = {
    "professor_nova_lab": ("Professor Nova'nın Laboratuvarı", "professor_nova_lab"),
    "kutuphane": ("Kütüphane", "kutuphane"),
    "tarih_muzesi": ("Tarih Müzesi", "tarih_muzesi"),
    "gelecek_teknoloji_lab": ("Gelecek Teknoloji Laboratuvarı", "gelecek_teknoloji_lab"),
    "gozlemevi": ("Gözlemevi", "gozlemevi"),
    "uzay_kontrol_merkezi": ("Uzay Kontrol Merkezi", "uzay_kontrol_merkezi"),
    "robot_atolyesi": ("Robot Atölyesi", "robot_atolyesi"),
    "kimya_laboratuvari": ("Kimya Laboratuvarı", "kimya_laboratuvari"),
    "ai_inovasyon_lab": ("AI İnovasyon Laboratuvarı", "ai_inovasyon_lab"),
    "dunya_cografya_odasi": ("Dünya ve Coğrafya Odası", "dunya_cografya_odasi"),
}

NO_LOCATION = "none"

# "Sahne Bazlı Otomatik Kadrolama" planı (kullanıcı onaylı): characters.
# AUTO_CHARACTER ile AYNI kavram, mekanlar için -- bkz. o sabitin
# docstring'i.
AUTO_LOCATION = "auto"


def location_descriptions_for_casting() -> dict[str, str]:
    """slug -> kısa mekan açıklaması, casting_generator'ın LLM prompt'una
    gömdüğü katalog için. Bkz. characters.character_descriptions_for_
    casting()'in docstring'i -- aynı gerekçe, i18n'den bağımsız.
    """
    return {
        "professor_nova_lab": "Professor Nova'nın kişisel \"Cosmic Lab\"ı -- kimya deneyleri, uzay temalı posterler.",
        "kutuphane": "Kitaplarla dolu sıcak bir kütüphane -- küreler, haritalar, okuma köşesi.",
        "tarih_muzesi": "Dinozor iskeletleri, antik Mısır ve şövalye sergileriyle dolu büyük bir müze.",
        "gelecek_teknoloji_lab": "Güneş sistemi ekranlı, robot kollu, teleskoplu fütüristik bir sınıf-laboratuvar.",
        "gozlemevi": "Dağ tepesinde, yıldızlı gökyüzü altında bir gözlemevi kubbesi.",
        "uzay_kontrol_merkezi": "Gezegen hologramlı, dünya manzaralı bir uzay kontrol merkezi.",
        "robot_atolyesi": "Çocukların robot inşa ettiği, devre şemalı bir atölye.",
        "kimya_laboratuvari": "Renkli deneylerin, kaynayan şişelerin yapıldığı bir kimya laboratuvarı.",
        "ai_inovasyon_lab": "Kuantum simülasyon ve DNA dizileme temalı fütüristik bir AI laboratuvarı.",
        "dunya_cografya_odasi": "Kıta hologramlı, yanardağ maketli bir coğrafya sınıfı.",
    }


def _data_uri(path: str) -> str:
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def get_location_reference(slug: str) -> CharacterReference:
    """Reads one location's reference image(s) from disk and returns a
    CharacterReference with real data-URI image fields, ready to combine
    with character_references before passing into
    run_pipeline(character_references=..., location_references=...).

    front.jpg is REQUIRED (KeyError/FileNotFoundError otherwise, same
    fail-loud contract as characters.get_character_reference).
    three_quarter.jpg/back.jpg are OPTIONAL -- included as extra reference
    angles only if present on disk, since these 10 locations currently
    ship with a single view each.
    """
    name, folder = _LOCATION_SLUGS[slug]
    base = utils.resource_dir(f"locations/{folder}")
    extra_refs = []
    for extra_view in ("three_quarter.jpg", "back.jpg"):
        path = f"{base}/{extra_view}"
        try:
            extra_refs.append(_data_uri(path))
        except FileNotFoundError:
            pass
    return CharacterReference(
        name=name,
        frontal_image_url=_data_uri(f"{base}/front.jpg"),
        reference_image_urls=extra_refs,
    )


def resolve_location_selection(selection: str) -> list[CharacterReference]:
    """`selection` is a raw value from the webui location card grid:
    NO_LOCATION ("none"), a single slug (a _LOCATION_SLUGS key), or any
    unknown value. Returns [] for NO_LOCATION/unknown, one entry for a
    known location -- mirrors
    characters.resolve_character_selection() exactly (no pair concept for
    locations -- a scene has at most one place).
    """
    if not selection or selection == NO_LOCATION:
        return []
    if selection in _LOCATION_SLUGS:
        return [get_location_reference(selection)]
    return []
