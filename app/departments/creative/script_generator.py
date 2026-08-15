"""Script stage: write per-scene narration lines sized to each scene's duration budget.

Also applies basic story-craft instructions (Hook/Retention/Callback) so the
outline's hook and closing actually make it into the narration -- previously
build_script_prompt() never saw the outline at all, which is why
quality_critic found real generations missing the hook/closing entirely.
"""

from app.config.profile_dimensions import Format, Tone
from app.models.outline import Outline
from app.models.scene import ScenePlan
from app.models.script import Script, ScriptLine
from app.services.documentary_llm_utils import generate_json

_WORDS_PER_SECOND = 2.3

DEFAULT_SCRIPT_SYSTEM_PROMPT = (
    "You are a scriptwriter for fast-paced, high-retention YouTube videos. "
    "Write natural, spoken-style narration -- no markdown, no scene labels, "
    "no 'narrator says'."
)

# Kullanıcı talimatı (2026-07-29): "sakin belgesel anlatıcısı" çerçevesi
# tamamen kaldırıldı -- her tonun ADI/enum değeri AYNI kaldı (DEFAULT_TONE_
# BY_CATEGORY hiç değişmedi), sadece açıklama metni "like a ... documentary
# narrator" kalıbından "like a ... YouTuber" kalıbına çevrildi. Her ton kendi
# duygusal aromasını (mysterious=merak, motivational=motivasyon, vb.) koruyor
# -- değişen sadece TESLİMAT tarzı: kısa/punchy cümleler, "never a slow/
# hushed/dry ..." ile eski belgesel temposunun açıkça reddi.
TONE_VOICE_GUIDANCE = {
    Tone.cinematic: "vivid and sensory, but fast-cut and punchy -- like a top travel YouTuber narrating quick cuts back-to-back, never lingering on one shot",
    Tone.credibility: "sharp and fact-packed, fired off in quick, quotable bursts -- like a top history YouTuber who opens with a bold claim and proves it fast, never a slow lecture",
    Tone.epic: "awe-struck and grand in scale, built from short, quotable lines racing toward one big payoff -- like a viral YouTube video that never lets the momentum drop",
    Tone.scientific: "clear and evidence-minded, but rapid-fire and hooky -- like a science YouTuber breaking down a study in quick, punchy beats, never a dry lecture",
    Tone.neutral: "clear, direct, and brisk -- plain language, zero filler, quick pacing, never dry or meandering",
    Tone.wondrous: "curious and awe-filled, reacting out loud in real time -- like a wildlife YouTuber marveling at vivid detail as it happens, never a slow, hushed narration",
    Tone.reflective: "calm and personal, but direct and present-tense -- like a YouTuber pausing mid-video to think out loud with you, never a detached, monotone voiceover",
    Tone.cinephile: "articulate and quick-witted, firing off enthusiasm in rapid takes -- like a popular YouTube film critic breaking down why a scene works, never a slow academic lecture",
    Tone.dynamic: "high-energy and relentless, building intensity beat by beat -- like a sports YouTuber hyping every highlight live, never a measured broadcast recap",
    Tone.encouraging: "warm and practical, but upbeat and direct -- like a health YouTuber firing off advice you can use today, never a slow clinical rundown",
    Tone.mysterious: "quick and intriguing, firing off one unanswered question after another -- like a true-crime YouTuber pulling you deeper into the case in real time, never a hushed, slow burn",
    Tone.motivational: "direct, high-energy, and practical -- like a motivational YouTuber firing off advice you can act on right now, never a slow, measured pep talk",
    Tone.savory: "warm and sensory, reacting fast to every bite -- like a food YouTuber devouring the moment on camera, never a slow, lingering food-doc narration",
    Tone.majestic: "grand and reverent, awed by scale, delivered in short punchy bursts -- like a landscape YouTuber reacting live to something vast, never a slow, reverent pan",
    Tone.gripping: "tense and fast-building, escalating stakes every beat -- like a thriller YouTuber racing toward the big reveal, never a slow, withholding prestige-doc pace",
    # "Bao" planı (kullanıcı onaylı): KASITLI İSTİSNA -- yukarıdaki her ton
    # bilerek "fast-paced, never slow/hushed/dry" (bkz. dosya üstü GÖREV 2
    # notu). Bu ton o kuralı BİLEREK ihlal ediyor: 3-8 yaş hedef kitlesi
    # için hızlı/yoğun tempo ZARARLI -- yavaş, sıcak, tekrarlayan bir ritim
    # bu tek istisnanın doğru davranışı (bkz. child_safe_guidance).
    Tone.nurturing: "warm, slow, and gentle, with simple words and clear pauses between ideas -- like a beloved children's show host speaking directly and patiently to a young child, never fast-paced or high-energy",
}

# Format is orthogonal to Tone: Tone shapes how the narration sounds (voice),
# Format shapes what job it does for the viewer (structure/purpose) -- an
# epic-toned space documentary can still be educational. `educational`,
# `corporate`, and `kids` are implemented; podcast is deliberately not
# modeled yet (see PROGRESS.md for why).
FORMAT_GUIDANCE = {
    Format.educational: (
        "structure this as an educational explainer -- briefly define any "
        "technical term the first time it appears, and close each scene "
        "with one natural spoken sentence that recaps what was just "
        "explained, spoken as part of the narration itself -- never write "
        "a literal label like 'Takeaway:' before it"
    ),
    Format.corporate: (
        "structure this as a corporate/institutional narrative -- avoid "
        "promotional or salesy language, use a neutral third-person voice "
        "instead of direct address, and ground claims in concrete data, "
        "figures, or verifiable facts rather than vague claims of excellence"
    ),
    Format.kids: (
        "structure this as a gentle children's story -- one simple scenario "
        "with a clear beginning, a small challenge, and a warm resolution "
        "that plainly demonstrates the episode's value, told directly to a "
        "young child listening at home. Do not invent or name any "
        "character, protagonist, or companion -- character casting happens "
        "in a later production stage this script has no visibility into, "
        "so an invented name would not match whoever (if anyone) actually "
        "appears on screen. Narrate directly to the viewer ('you'll see...', "
        "'let's look at...') instead, or, only if the scenario truly needs a "
        "subject, use an unnamed generic one ('a curious explorer', 'a "
        "friend') -- never a proper name"
    ),
}


def _story_craft_instructions(scene_plan: ScenePlan, outline: Outline | None) -> str:
    instructions = []
    if outline and outline.hook.strip():
        instructions.append(
            "- Hook: scene 0's narration must open with or directly deliver this "
            f'hook, adapted into natural spoken narration: "{outline.hook.strip()}"'
        )
    if len(scene_plan.scenes) > 1:
        instructions.append(
            "- Retention: end most scenes on a forward-pulling detail, tension, "
            "or open question rather than a fully resolved statement, so the "
            "viewer wants to see what happens next -- across the narration as "
            "a whole, a new concrete detail or turn should surface every "
            "couple of scenes so the pacing never goes flat."
        )
    if outline and outline.closing.strip():
        instructions.append(
            "- Callback: the LAST scene's narration must deliver a closing that "
            "circles back to the hook and/or delivers this closing beat: "
            f'"{outline.closing.strip()}"'
        )
    if not instructions:
        return ""
    return "\n\nStory craft requirements:\n" + "\n".join(instructions)


# GÖREV 3 (kullanıcı onaylı, TAM OTONOMİ): platform büyüme/monetizasyon
# ilkeleri -- Tone/Format gibi kullanıcı seçimi DEĞİL, Hook/Retention/
# Callback ile aynı "her zaman açık, kapatılamaz" kategori. Kullanıcı
# hiçbir yeni seçenek görmüyor/seçmiyor -- webui'de toggle yok.
def _growth_guidance_instructions(format: Format | None) -> str:
    """Platform-growth requirements applied to every generation unconditionally.

    Format.corporate explicitly asks for a "neutral third-person voice" and
    to "avoid promotional or salesy language" -- a subscribe-style nudge or a
    direct audience-engagement question would undercut that institutional
    tone, so those two lines are suppressed specifically for that format.
    The opening/ad-safe/series-feel lines still apply everywhere since they
    don't conflict with a neutral voice.
    """
    lines = [
        "- Opening: the first ~8 seconds must open with a concrete, specific "
        "detail about this topic -- never a generic greeting, throat-clearing, "
        "or scene-setting preamble.",
        "- Advertiser-safe: do not include graphic violence, hate speech, or "
        "sensational/unverified claims.",
        "- Series feel: where it fits naturally, hint that this topic connects "
        "to a broader pattern or theme, without inventing a connection that "
        "isn't true.",
    ]
    if format != Format.corporate:
        lines.append(
            "- Closing nudge: end with a brief, non-pushy invitation to keep "
            "watching or follow along, phrased as a natural continuation of "
            "the story rather than a jingle or direct sales pitch."
        )
        # "Bao" planı (kullanıcı onaylı): "yorum yap" davetini küçük çocuklara
        # yöneltmek uygun değil -- bu satır kids için de bastırılıyor, ama
        # yukarıdaki "Closing nudge" (bir sonraki bölümü izlemeye davet)
        # kids için BİLEREK korunuyor (zararsız, çocuk içeriğinde standart).
        if format != Format.kids:
            lines.append(
                "- Engagement: include one natural open-ended question or "
                "invitation for the viewer's own view on the topic, phrased so it "
                "could prompt a reply -- not a forced or robotic call to comment."
            )
    return "\n\nGrowth requirements:\n" + "\n".join(lines)


# "Bao" planı (kullanıcı onaylı, ÇOCUK GÜVENLİĞİ -- ZORUNLU, kapatılamaz):
# _growth_guidance_instructions ile AYNI desen (her zaman açık, webui'de
# toggle yok) ama TERSİ etkiyle -- o, her formata bir şeyler EKLİYOR; bu,
# SADECE format == Format.kids olduğunda bir şey ekliyor, aksi halde no-op.
# docs/future-work.md'nin "vocabulary-only kids mode ASLA gönderilmemeli"
# uyarısını karşılamak için var -- Format.kids'i BU fonksiyon olmadan asla
# kullanma.
def _child_safe_guidance_instructions(format: Format | None) -> str:
    if format != Format.kids:
        return ""
    lines = [
        "- Age-appropriate language: vocabulary and sentence structure a "
        "3-8 year old understands -- short sentences, common words, no "
        "abstract or complex vocabulary.",
        "- No violence: no fighting, weapons, physical harm, or threats, "
        "even played for comedy or as cartoon slapstick.",
        "- No death or serious peril: no character death, near-death "
        "danger, or life-threatening situations -- conflicts resolve "
        "through kindness, sharing, or cooperation, never through danger.",
        "- No scary imagery or atmosphere: no monsters, jump-scares, or "
        "content designed to frighten.",
        "- No frightening real-world topics: no war, loss of a family "
        "member, illness, or other real-world fears -- teach the episode's "
        "value (e.g. courage) through a gentle, everyday scenario (helping "
        "a friend, sharing a toy), never through danger or loss.",
        "- Positive resolution: every episode ends with the value clearly "
        "and warmly demonstrated -- no ambiguous or unresolved ending.",
        "- No commercial pressure: no calls to buy anything, no brand "
        "mentions.",
    ]
    return "\n\nChild safety requirements (mandatory for kids content):\n" + "\n".join(lines)


# "CTA/Etkileşim Formatlı Short Videolar" planı (kullanıcı onaylı): halihazırda
# kullanıcının 6 aylık içerik takviminde somutlaşmış bir format -- haftanın
# 4 short'undan biri bilgilendirici değil, doğrudan bir SORU/CTA taşıyor (ör.
# "Uzayda En Çok Neyi Merak Ediyorsun? Yorumlarda Söyle!", "Sen Olsan Nasıl
# Bir Robot Tasarlardın?"). `_growth_guidance_instructions`'ın genel
# "Engagement:" satırından (orada TEK cümle, opsiyonel bir ek, kids formatı
# için BASTIRILIYOR) BİLEREK FARKLI/DAHA GÜÇLÜ: burada soru videonun
# MERKEZİ, ve kids formatında da KASITLI OLARAK bastırılmıyor -- kullanıcının
# kendi örneği ("Sen Olsan Nasıl Bir Robot Tasarlardın?") zaten kids içerikte
# kullanılan bir CTA. Varsayılan "informational" ile HİÇBİR davranış
# değişmez (no-op) -- regresyon garantisi.
_ENGAGEMENT_CTA_GUIDANCE = (
    "\n\nEngagement format: this is a short, casual, QUESTION-driven video, "
    "not an information dump -- a brief, vivid setup (1-2 scenes) is enough "
    "context, then pivot to directly asking the viewer a specific, "
    "easy-to-answer question about the topic, inviting them to answer in "
    "the comments. The question is the HEART of the video, not an "
    "afterthought tacked onto the end -- most of the narration should "
    "build curiosity toward it rather than explain facts. This applies "
    "even in a kids-format episode (a gentle, age-appropriate question "
    "like 'what kind of robot would you build?' is exactly right there)."
)


def _engagement_cta_instructions(video_style: str) -> str:
    if video_style != "engagement_cta":
        return ""
    return _ENGAGEMENT_CTA_GUIDANCE


def build_script_prompt(
    scene_plan: ScenePlan,
    topic: str,
    language: str = "",
    custom_system_prompt: str = "",
    outline: Outline | None = None,
    tone: Tone | None = None,
    format: Format | None = None,
    custom_requirements: str = "",
    video_style: str = "informational",
) -> str:
    scene_lines = []
    for scene in scene_plan.scenes:
        target_words = max(5, round(scene.duration_seconds * _WORDS_PER_SECOND))
        scene_lines.append(
            f'- scene {scene.index} ("{scene.title}"): {scene.narration_beat} '
            f"[~{target_words} words, ~{scene.duration_seconds:.0f}s]"
        )
    scenes_block = "\n".join(scene_lines)

    # GÖREV F takibi (kullanıcı bulgusu): custom_system_prompt eskiden
    # DEFAULT_SCRIPT_SYSTEM_PROMPT'un YERİNE geçiyordu -- gerçek doğrulamada
    # "Write like a noir detective." gibi zararsız görünen bir stil isteği
    # bile "no markdown, no scene labels, no narrator says" korumasını
    # sessizce siliyordu. custom_requirements ile TUTARSIZ bir asimetriydi
    # (o zaten ek/additive). Artık custom_system_prompt de additive: temel
    # talimat HER ZAMAN kalıyor, kullanıcının isteği onun yanına ek stil
    # rehberliği olarak ekleniyor.
    prompt = DEFAULT_SCRIPT_SYSTEM_PROMPT
    if custom_system_prompt.strip():
        prompt += f"\n\nAdditional style guidance:\n{custom_system_prompt.strip()}"
    prompt += f"""

Topic: "{topic}"

Write one narration line per scene below, matching its target word count as
closely as possible so the timing lines up with the scene's on-screen duration:
{scenes_block}"""
    if tone is not None:
        voice = TONE_VOICE_GUIDANCE.get(tone, TONE_VOICE_GUIDANCE[Tone.neutral])
        prompt += f"\n\nVoice: {voice}."
    if format is not None:
        format_guidance = FORMAT_GUIDANCE.get(format)
        if format_guidance:
            prompt += f"\n\nFormat: {format_guidance}."
    prompt += _story_craft_instructions(scene_plan, outline)
    prompt += _growth_guidance_instructions(format)
    prompt += _child_safe_guidance_instructions(format)
    prompt += _engagement_cta_instructions(video_style)
    # GÖREV F (kullanıcı onaylı): kullanıcının kendi ek talimatları --
    # otomatik büyüme ilkelerinin (yukarıdaki _growth_guidance_instructions)
    # YERİNE değil, onun HEMEN ARDINA ek bir blok olarak ekleniyor, böylece
    # ikisi çakışmıyor/birbirini ezmiyor.
    if custom_requirements.strip():
        prompt += f"\n\nAdditional requirements:\n{custom_requirements.strip()}"
    if language and language != "auto":
        prompt += f"\n\nRespond in language: {language}"
    prompt += """

Respond with a single JSON object with exactly this shape:
{"lines": [{"scene_index": 0, "text": "..."}]}
Include exactly one entry per scene index listed above, in order. Do not include
any other text, markdown, or scene titles inside the narration text itself."""
    return prompt


def _parse_lines(raw: list) -> dict[int, str]:
    lines_by_index = {}
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("scene_index"))
        except (TypeError, ValueError):
            continue
        text = str(item.get("text", "")).strip()
        if text:
            lines_by_index[idx] = text
    return lines_by_index


def generate_script(
    scene_plan: ScenePlan,
    topic: str,
    language: str = "",
    custom_system_prompt: str = "",
    outline: Outline | None = None,
    tone: Tone | None = None,
    format: Format | None = None,
    custom_requirements: str = "",
    video_style: str = "informational",
) -> Script:
    if not scene_plan.scenes:
        return Script(full_text="", lines=[], language=language)

    prompt = build_script_prompt(
        scene_plan,
        topic,
        language,
        custom_system_prompt,
        outline=outline,
        tone=tone,
        format=format,
        custom_requirements=custom_requirements,
        video_style=video_style,
    )
    data = generate_json(prompt)
    lines_by_index = _parse_lines(data.get("lines", []))

    lines = [
        ScriptLine(scene_index=scene.index, text=lines_by_index.get(scene.index) or scene.narration_beat)
        for scene in scene_plan.scenes
    ]
    full_text = "\n\n".join(line.text for line in lines)
    return Script(full_text=full_text, lines=lines, language=language)
