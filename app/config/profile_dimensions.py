"""Documentary pipeline profile dimensions: topic category, pacing, language."""

from enum import Enum


class TopicCategory(str, Enum):
    travel = "travel"
    history = "history"
    space = "space"
    psychology = "psychology"
    marine = "marine"
    spiritual = "spiritual"
    film_highlights = "film_highlights"
    sports = "sports"
    healthy_living = "healthy_living"
    mysterious_discoveries = "mysterious_discoveries"
    personal_development = "personal_development"
    food_culture = "food_culture"
    nature = "nature"
    netflix_style = "netflix_style"
    # "Bao" planı (kullanıcı onaylı): çocuklara yönelik değerler eğitimi
    # içeriği -- personal_development'tan KASITLI olarak ayrı (o kategori
    # yetişkinlere yönelik çerçeveli, "somut hikayeler/araştırma" istiyor;
    # bu, 3-8 yaş için tamamen farklı bir ses/güvenlik profili gerektiriyor).
    values_education = "values_education"


class Tone(str, Enum):
    cinematic = "cinematic"
    credibility = "credibility"
    epic = "epic"
    scientific = "scientific"
    neutral = "neutral"
    wondrous = "wondrous"
    reflective = "reflective"
    cinephile = "cinephile"
    dynamic = "dynamic"
    encouraging = "encouraging"
    mysterious = "mysterious"
    motivational = "motivational"
    savory = "savory"
    majestic = "majestic"
    gripping = "gripping"
    # "Bao" planı: diğer 15 tonun HEPSİ kasıtlı olarak "fast-paced, punchy,
    # never slow" (bkz. script_generator.py, 3bc21c2 + gece oturumu
    # "documentary" temizliği) -- bu, KASITLI bir istisna. 3-8 yaş için
    # yavaş, sakin, tekrarlayan bir ritim doğru olan, "fast-paced YouTube"
    # kalıbının çocuk içeriğinde ZARARLI olacağı TEK ton.
    nurturing = "nurturing"


# One default tone per topic category, chosen to match each category's
# existing PROFILE_PROMPTS template exactly (travel=cinematic,
# history=credibility, space=epic, psychology=scientific) -- resolve_tone()
# with no override must reproduce today's category-locked behavior.
DEFAULT_TONE_BY_CATEGORY = {
    TopicCategory.travel: Tone.cinematic,
    TopicCategory.history: Tone.credibility,
    TopicCategory.space: Tone.epic,
    TopicCategory.psychology: Tone.scientific,
    TopicCategory.marine: Tone.wondrous,
    TopicCategory.spiritual: Tone.reflective,
    TopicCategory.film_highlights: Tone.cinephile,
    TopicCategory.sports: Tone.dynamic,
    TopicCategory.healthy_living: Tone.encouraging,
    TopicCategory.mysterious_discoveries: Tone.mysterious,
    TopicCategory.personal_development: Tone.motivational,
    # OTONOM KARAR (gündüz oturumu): her yeni kategori kendi özel tonunu
    # alıyor, mevcut bir tonu paylaşmıyor -- aksi halde alakasız bir stil
    # metni (ör. "Sports documentary...") o kategoriye gider (bkz. bugünkü
    # 7 kategori genişlemesinde aynı gerekçe). food_culture -> savory (yeni
    # tone, duyusal/lezzet odaklı); nature -> majestic (yeni tone, marine'in
    # "wondrous"undan kasıtlı olarak ayrı -- marine su altına özel,
    # nature kara/orman/dağ ölçeğine odaklanıyor); netflix_style -> gripping
    # (yeni tone, premium/suspenseful prodüksiyon stili -- "cinephile"
    # (film_highlights, filmleri ANALİZ eden) ile karıştırılmasın diye
    # kasıtlı olarak ayrı).
    TopicCategory.food_culture: Tone.savory,
    TopicCategory.nature: Tone.majestic,
    TopicCategory.netflix_style: Tone.gripping,
    # "Bao" planı (kullanıcı onaylı): values_education her zaman nurturing --
    # tone_override yolu teorik olarak var ama bu kategori için başka bir
    # tonun anlamı yok (bkz. yukarıdaki nurturing tanımı).
    TopicCategory.values_education: Tone.nurturing,
}


class Format(str, Enum):
    """What kind of content this is (independent of Tone, which is how it
    sounds, and Pacing, which is how long/fast it is). `educational`,
    `corporate`, and `kids` are implemented -- podcast is deliberately not
    modeled here yet; see PROGRESS.md for why.

    `kids` MUST always be paired with the mandatory
    `_child_safe_guidance_instructions()` layer in script_generator.py --
    see docs/future-work.md's original warning against shipping a
    vocabulary-only kids mode without a real safety layer. Never treat
    `kids` as just another style/vocabulary switch.
    """

    educational = "educational"
    corporate = "corporate"
    kids = "kids"


class Pacing(str, Enum):
    short = "short"
    long = "long"
    # GÖREV 2 (TAM OTONOMİ): uzun-form video (10+ dakika). "Daha fazla sahne"
    # (short'un 4 sahnesinden) VE "sahne başına daha uzun anlatım" (short'un
    # 5sn'sinden) arasında bir orta yol seçildi -- ne LLM'e tek seferde 60+
    # sahne üretme yükü bindiriliyor (kalite riski), ne de tek bir sahneye
    # 60sn+ kesintisiz anlatım yükleniyor (monoton akış riski, GROWTH_
    # GUIDANCE'ın "her birkaç sahnede yeni detay" ilkesiyle çelişirdi).
    extended = "extended"


class Language(str, Enum):
    """Documentary Studio's own topic language -- independent of webui's
    `locales` (UI translation language, 9 values) and the legacy pipeline's
    `support_locales` (11-value "Script Language" list). Adding a language
    here does not add it to either of those; see webui/Main.py's note next
    to `locales` (GÖREV 8d, PROGRESS.md) for the full picture."""

    auto = "auto"
    tr = "tr"
    en = "en"


# Scene count / per-scene duration budget used by ScenePlanner, keyed by pacing.
# short: 7 scenes x 5s = 35s (a "Shorts"-length clip).
# long: 10 scenes x 30s = 300s (5 minutes) -- kullanıcı onaylı (2026-08-15):
# önceden 7x8s=56s idi ("uzun Shorts"), şimdi gerçek bir orta-uzunluk video
# (5dk). extended'in AYNI 30s/sahne yoğunluğunu kullanıyor (sadece yarısı
# kadar sahne) -- iki tier arasında tutarlı bir anlatım temposu.
# extended: 20 scenes x 30s = 600s (10 minutes) exactly.
#
# short.scene_count was 4 until a real production bug was diagnosed
# (PROGRESS.md "Video-anlatım uyumsuzluğu" -- three real generations, ALL
# of them lost 33-43% of their outline sections to scene_planner's
# importance-based trimming, since outline_generator routinely produces
# 6-7 sections for "short" but only 4 scenes were ever kept). Raised to 7
# to match short's OWN outline ceiling (PACING_OUTLINE_SECTION_RANGE below).
PACING_SCENE_SPEC = {
    Pacing.short: {"scene_count": 7, "scene_duration": 5.0},
    Pacing.long: {"scene_count": 10, "scene_duration": 30.0},
    Pacing.extended: {"scene_count": 20, "scene_duration": 30.0},
}

# outline_generator asks the LLM for a range of sections, not an exact count,
# so scene_planner's importance-based trimming has real material to work
# with. short's value is the EXACT hardcoded range outline_generator used
# before this became pacing-aware -- byte-identical behavior, zero
# regression. long/extended need wider ranges since their scene_count (10/20)
# is far beyond what a single "4-7" outline could ever supply -- long's
# range is extended's (18-24 for 20 scenes) scaled down to its own 10-scene
# budget (same ~0.9x/1.2x ratio).
PACING_OUTLINE_SECTION_RANGE = {
    Pacing.short: (4, 7),
    Pacing.long: (9, 12),
    Pacing.extended: (18, 24),
}


def resolve_topic_category(value: str | TopicCategory | None) -> TopicCategory | None:
    if value is None or value == "":
        return None
    if isinstance(value, TopicCategory):
        return value
    try:
        return TopicCategory(str(value).strip().lower())
    except ValueError:
        return None


def resolve_tone(
    topic_category: str | TopicCategory | None,
    tone_override: str | Tone | None = None,
) -> Tone:
    if tone_override not in (None, ""):
        if isinstance(tone_override, Tone):
            return tone_override
        try:
            return Tone(str(tone_override).strip().lower())
        except ValueError:
            pass  # invalid override string -- fall through to the category default
    category = resolve_topic_category(topic_category)
    return DEFAULT_TONE_BY_CATEGORY.get(category, Tone.neutral)


def resolve_format(value: str | Format | None) -> Format | None:
    if value is None or value == "":
        return None
    if isinstance(value, Format):
        return value
    try:
        return Format(str(value).strip().lower())
    except ValueError:
        return None


def resolve_pacing(value: str | Pacing | None, default: Pacing = Pacing.short) -> Pacing:
    if value is None or value == "":
        return default
    if isinstance(value, Pacing):
        return value
    try:
        return Pacing(str(value).strip().lower())
    except ValueError:
        return default
