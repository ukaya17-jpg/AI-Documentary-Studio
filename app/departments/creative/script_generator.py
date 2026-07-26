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
    "You are a documentary narration scriptwriter. Write natural, spoken-style "
    "narration -- no markdown, no scene labels, no 'narrator says'."
)

# Previously the narration writer never saw the topic's tone at all -- only
# outline_generator/research_planner read PROFILE_PROMPTS. This is a new
# addition, not a re-keyed existing behavior, so there is no old text to stay
# byte-identical to; it's additive and only applies when a tone is passed in.
TONE_VOICE_GUIDANCE = {
    Tone.cinematic: "vivid, immersive, and sensory -- like a travel film voiceover",
    Tone.credibility: "measured, authoritative, and precise -- like a trusted history documentary narrator",
    Tone.epic: "awe-struck and grand in scale, while staying clear and grounded",
    Tone.scientific: "clear, evidence-minded, and approachable -- like explaining research to a curious friend",
    Tone.neutral: "clear and neutral",
    Tone.wondrous: "curious and awe-filled, savoring vivid natural detail -- like a nature documentary narrator marveling at what's on screen",
    Tone.reflective: "calm, unhurried, and contemplative -- like a narrator inviting quiet reflection rather than reciting facts",
    Tone.cinephile: "articulate and analytical, with genuine enthusiasm for craft -- like a film critic explaining why a scene works",
    Tone.dynamic: "energetic and momentum-driven, building intensity toward key moments -- like a sports broadcast narrator",
    Tone.encouraging: "warm, practical, and supportive -- like a knowledgeable friend giving grounded health advice",
    Tone.mysterious: "hushed and intriguing, building curiosity without sensationalizing -- like a narrator walking through an unsolved case",
    Tone.motivational: "direct, energizing, and practical -- like a coach giving advice you can act on immediately",
    Tone.savory: "warm and sensory, lingering on taste and texture -- like a food documentary narrator savoring every bite",
    Tone.majestic: "grand and reverent, awed by scale -- like a nature documentary narrator standing before something vast",
    Tone.gripping: "tense and controlled, building suspense -- like a premium streaming documentary narrator withholding just enough",
}

# Format is orthogonal to Tone: Tone shapes how the narration sounds (voice),
# Format shapes what job it does for the viewer (structure/purpose) -- an
# epic-toned space documentary can still be educational. `educational` and
# `corporate` are implemented; podcast/kids are deliberately not modeled yet
# (see PROGRESS.md for why each needs its own separate decision).
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
        lines.append(
            "- Engagement: include one natural open-ended question or "
            "invitation for the viewer's own view on the topic, phrased so it "
            "could prompt a reply -- not a forced or robotic call to comment."
        )
    return "\n\nGrowth requirements:\n" + "\n".join(lines)


def build_script_prompt(
    scene_plan: ScenePlan,
    topic: str,
    language: str = "",
    custom_system_prompt: str = "",
    outline: Outline | None = None,
    tone: Tone | None = None,
    format: Format | None = None,
) -> str:
    scene_lines = []
    for scene in scene_plan.scenes:
        target_words = max(5, round(scene.duration_seconds * _WORDS_PER_SECOND))
        scene_lines.append(
            f'- scene {scene.index} ("{scene.title}"): {scene.narration_beat} '
            f"[~{target_words} words, ~{scene.duration_seconds:.0f}s]"
        )
    scenes_block = "\n".join(scene_lines)

    prompt = custom_system_prompt or DEFAULT_SCRIPT_SYSTEM_PROMPT
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
    )
    data = generate_json(prompt)
    lines_by_index = _parse_lines(data.get("lines", []))

    lines = [
        ScriptLine(scene_index=scene.index, text=lines_by_index.get(scene.index) or scene.narration_beat)
        for scene in scene_plan.scenes
    ]
    full_text = "\n\n".join(line.text for line in lines)
    return Script(full_text=full_text, lines=lines, language=language)
