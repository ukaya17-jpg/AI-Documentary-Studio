"""Casting stage: pick a per-scene character/location from the fixed
Kling-O1-reference catalogs (app.config.characters / app.config.locations)
-- ONLY runs in "Auto" mode (see default_pipeline.py's
`character_selection`/`location_selection` == AUTO_CHARACTER/AUTO_LOCATION).

"Sahne Bazlı Otomatik Kadrolama" planı (kullanıcı onaylı): sabit-tüm-video
seçiminin (bir slug elle seçilmiş) tersine, Auto modda hangi karakter/mekanın
HANGİ sahnede göründüğü konuya göre DEĞİŞEBİLİR -- bir sahne kütüphanede
geçebilir, bir sonraki uzay kontrol merkezinde. Bu modül SADECE bu kararı
verir (hangi sahnede hangi slug); gerçek referans görsellerini disk'ten okuma
işi hâlâ characters.get_character_reference()/locations.get_location_
reference()'ta -- burası sadece bir "slug seçici", storyboard_generator'ın
"shot seçici" olması gibi.
"""

from loguru import logger

from app.models.script import Script
from app.models.storyboard import Storyboard
from app.services.documentary_llm_utils import generate_json

# "Çoklu Karakter Aynı Sahnede" planı (kullanıcı onaylı): fal.ai Kling O1
# Reference-to-Video'nun gerçek `elements[]` şeması "max 7 total (elements +
# image_urls + implicit start frame)" diyor (bkz.
# docs/character-consistency-research.md) -- image_urls hiç kullanılmıyor,
# implicit start frame 1 slot yiyor, geriye 6 kullanılabilir element
# kalıyor. Bu proje bir sahnede karakterlerin YANINDA bir de mekan (1 element
# daha) seçebiliyor, o yüzden pratik üst sınır 3 karakter + 1 mekan = 4 --
# API'nin sert 6 sınırının altında, güvenli bir marj bırakıyor.
_MAX_CHARACTERS_PER_SCENE = 3

# Kullanıcı onaylı taslak (bkz. konuşma geçmişi) -- karakter/mekan
# kataloğu buraya SABİT KODLANMADI, _character_catalog_block()/
# _location_catalog_block() ile app.config.characters/locations'tan
# DİNAMİK üretiliyor (registry'ye yeni bir karakter/mekan eklendiğinde bu
# prompt'un da elle güncellenmesi gerekmesin diye).
_SYSTEM_PROMPT_TEMPLATE = """Sen bir eğitici çizgi film serisinin "kadrolama" (casting) editörüsün.
Sana bölümün TAM SENARYOSU (sahne sahne anlatım metni) ve İKİ SABİT
KATALOG verilecek: mevcut KARAKTERLER ve mevcut MEKANLAR.

Görevin: her sahne için (varsa) hangi karakter(ler)in konuşacağını/
görüneceğini ve hangi mekanda geçtiğini seçmek -- SADECE aşağıdaki
kataloglardan, başka hiçbir isim uydurmadan.

KARAKTERLER:
{character_catalog}

MEKANLAR:
{location_catalog}

SAHNELER:
{scenes_block}

KURALLAR:
1. Her sahnenin konusuna EN UYGUN karakter(ler)i/mekanı seç. Hiçbiri uygun
   değilse boş liste/null bırak (karaktersiz/mekansız sahne tamamen
   normaldir).
2. Çoğu sahne TEK bir karakter içerir. Bir sahnede birden fazla karakter
   AYNI ANDA görünmesi gerçekten doğruysa (ör. iki karakterin birlikte
   konuştuğu bir an) "characters" listesine en fazla {max_characters}
   karakter, ÖNCELİK SIRASINA göre (en önemli/en çok konuşan ÖNCE) ekle --
   fazlasını uydurma, gerçekten gerekmiyorsa TEK karakter yeterlidir.
3. Aynı karakter/mekan art arda birkaç sahnede tekrar edebilir (doğal bir
   akış için gerekli) -- her sahnede değiştirmek ZORUNLU değil.
4. Konuyla hiç ilgisi olmayan bir karakteri/mekanı ZORLA sahneye sokma.
5. SADECE JSON döndür, başka hiçbir metin ekleme, tam olarak bu şekilde
   (her sahne index'i için bir giriş, "characters" yukarıdaki katalogdan
   0-{max_characters} slug içeren bir liste, "location" bir slug ya da null):
{{"casting": [{{"scene_index": 0, "characters": ["professor_nova"], "location": "kimya_laboratuvari"}}]}}"""


def _character_catalog_block(character_descriptions: dict[str, str]) -> str:
    if not character_descriptions:
        return "(katalog boş -- her sahne için characters: [] döndür)"
    return "\n".join(f"- {slug}: {desc}" for slug, desc in character_descriptions.items())


def _location_catalog_block(location_descriptions: dict[str, str]) -> str:
    if not location_descriptions:
        return "(katalog boş -- her sahne için location: null döndür)"
    return "\n".join(f"- {slug}: {desc}" for slug, desc in location_descriptions.items())


def build_casting_prompt(
    storyboard: Storyboard,
    script: Script,
    character_descriptions: dict[str, str],
    location_descriptions: dict[str, str],
) -> str:
    lines_by_scene = {line.scene_index: line.text for line in script.lines}
    scene_blocks = [
        f'- scene {shot.scene_index}: "{lines_by_scene.get(shot.scene_index, shot.description)}"'
        for shot in storyboard.shots
    ]
    return _SYSTEM_PROMPT_TEMPLATE.format(
        character_catalog=_character_catalog_block(character_descriptions),
        location_catalog=_location_catalog_block(location_descriptions),
        scenes_block="\n".join(scene_blocks),
        max_characters=_MAX_CHARACTERS_PER_SCENE,
    )


def _parse_character_slugs(raw_characters, valid_character_slugs: set, scene_index: int) -> list[str]:
    """"Çoklu Karakter Aynı Sahnede" planı: LLM'in döndürdüğü "characters"
    listesini, kataloğa ait olmayan (halüsinasyon) her slug'ı SESSİZCE
    atarak, geçerli slug'ların SIRASINI koruyarak (liste sırası =
    casting_generator'ın kendi önem sırası, ses seçiminde de bu sıra
    kullanılıyor -- bkz. audio_renderer._resolve_scene_voice) temizler.
    _MAX_CHARACTERS_PER_SCENE'i aşan fazlalık, en düşük öncelikli
    (listenin SONUNDAKİ) karakterlerden düşürülür, WARNING loglanır --
    fal.ai Kling O1'in gerçek element sayısı sınırını (bkz. modül üstü
    yorum) aşan bir istek göndermemek için.
    """
    if not isinstance(raw_characters, list):
        return []
    valid_slugs = [slug for slug in raw_characters if slug in valid_character_slugs]
    if len(valid_slugs) > _MAX_CHARACTERS_PER_SCENE:
        logger.warning(
            f"casting_generator: scene {scene_index} got {len(valid_slugs)} characters, "
            f"capping to {_MAX_CHARACTERS_PER_SCENE} (dropped: {valid_slugs[_MAX_CHARACTERS_PER_SCENE:]})"
        )
        valid_slugs = valid_slugs[:_MAX_CHARACTERS_PER_SCENE]
    return valid_slugs


def _parse_casting(raw: list, valid_character_slugs: set, valid_location_slugs: set) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("scene_index"))
        except (TypeError, ValueError):
            continue
        character_slugs = _parse_character_slugs(item.get("characters"), valid_character_slugs, idx)
        location_slug = item.get("location")
        if location_slug not in valid_location_slugs:
            location_slug = None
        result[idx] = {"characters": character_slugs, "location": location_slug}
    return result


def generate_casting_plan(
    storyboard: Storyboard,
    script: Script,
    character_descriptions: dict[str, str],
    location_descriptions: dict[str, str],
) -> dict[int, dict]:
    """Returns {scene_index: {"characters": list[slug], "location": slug|None}}
    for every shot in `storyboard` -- scenes the LLM omits, or where it
    hallucinates unregistered slugs, resolve to {"characters": [],
    "location": None} (silently, not an error -- a scene with no
    character/location reference is a completely normal, valid outcome,
    same as picking "Karaktersiz"/"Mekansız" manually). `characters` is
    ordered by the LLM's own priority (see _parse_character_slugs) and
    capped at _MAX_CHARACTERS_PER_SCENE.
    """
    if not storyboard.shots or (not character_descriptions and not location_descriptions):
        return {}
    prompt = build_casting_prompt(storyboard, script, character_descriptions, location_descriptions)
    data = generate_json(prompt)
    parsed = _parse_casting(
        data.get("casting", []), set(character_descriptions), set(location_descriptions)
    )
    # Bahsi geçmeyen sahneler icin varsayilan bos giris (asset_generator'in
    # her scene_index icin bir sozluk girisi bulacagini garanti eder).
    for shot in storyboard.shots:
        parsed.setdefault(shot.scene_index, {"characters": [], "location": None})
    return parsed
