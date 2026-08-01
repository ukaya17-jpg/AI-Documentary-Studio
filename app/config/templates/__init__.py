"""Outline templates per Tone.

Each template is a plain dict of guidance strings plugged into the outline
generation prompt: how to open the video, what kind of sections to favor,
and how to close. ``PROFILE_PROMPTS`` keys mirror
``app.config.profile_dimensions.Tone`` values.

Previously keyed directly by ``TopicCategory`` (one hard-locked tone per
category); re-keyed by ``Tone`` so a topic's tone can be resolved
independently of its category (see ``resolve_tone``). The template content
itself is unchanged -- each category's former slot now sits under that
category's default tone (travel->cinematic, history->credibility,
space->epic, psychology->scientific), so resolving with no override
reproduces the exact same prompt text as before.

GÖREV 2 (gece oturumu): every ``"style"`` entry used to open with "X
documentary." -- this fed outline/research generation (hook, closing,
section structure), so even after script_generator's own voice/system
prompt was rewritten to be YouTube-dynamic (3bc21c2, prior session), the
CONTENT it was asked to narrate (the outline's hook/sections/closing) was
still conceived under an explicit documentary framing, and that feel
carried through regardless of the final delivery voice. Every "style" line
now opens with "X YouTube video." and ends with a "delivered like a ...
YouTuber..." clause mirroring the SAME persona already used in
``script_generator.TONE_VOICE_GUIDANCE`` for that tone, so outline/
research/script generation now pull in the same direction. Every other
field (opening_hook/section_guidance/closing) was already style-neutral
narrative-craft guidance and is unchanged.
"""

from app.config.profile_dimensions import Tone

PROFILE_PROMPTS = {
    Tone.cinematic: {
        "style": (
            "Travel YouTube video. Ground the narration in concrete sensory detail "
            "(sights, sounds, food, local life) and a strong sense of place, "
            "delivered like a top travel YouTuber narrating quick cuts "
            "back-to-back, never lingering on one shot."
        ),
        "opening_hook": (
            "Open with a vivid, specific moment or image from the destination, "
            "not a generic welcome."
        ),
        "section_guidance": (
            "Cover history/context, standout landmarks or experiences, culture and "
            "daily life, and one surprising or lesser-known fact."
        ),
        "closing": "End with a reflective takeaway or an invitation to explore further.",
    },
    Tone.credibility: {
        "style": (
            "History YouTube video. Prioritize chronological or cause-effect clarity "
            "and named people, dates, and turning points, delivered like a top "
            "history YouTuber who opens with a bold claim and proves it fast, "
            "never a slow lecture."
        ),
        "opening_hook": (
            "Open with a pivotal moment or dramatic stakes before backing up to context."
        ),
        "section_guidance": (
            "Cover origins/context, the key turning point(s), consequences, and how "
            "it echoes into the present."
        ),
        "closing": "End by tying the historical event to its lasting significance.",
    },
    Tone.epic: {
        "style": (
            "Space/science YouTube video. Favor scale, precision, and awe; translate "
            "technical facts into vivid comparisons a general audience can grasp, "
            "delivered like a viral YouTube video that never lets the momentum "
            "drop."
        ),
        "opening_hook": (
            "Open with a striking scale comparison or an unresolved mystery."
        ),
        "section_guidance": (
            "Cover the core phenomenon or discovery, how we know what we know, "
            "current open questions, and why it matters."
        ),
        "closing": "End by widening the lens to what this means for our understanding of the universe.",
    },
    Tone.scientific: {
        "style": (
            "Psychology YouTube video. Ground abstract concepts in a relatable "
            "scenario or experiment before generalizing, delivered like a "
            "science YouTuber breaking down a study in quick, punchy beats, "
            "never a dry lecture."
        ),
        "opening_hook": (
            "Open with a relatable everyday scenario or a counterintuitive question."
        ),
        "section_guidance": (
            "Cover the phenomenon, the research/evidence behind it, real-world "
            "implications, and practical takeaways."
        ),
        "closing": "End with a practical takeaway the viewer can apply to their own life.",
    },
    Tone.wondrous: {
        "style": (
            "Marine/nature YouTube video. Ground the narration in vivid sensory "
            "detail of the underwater world (light, motion, scale) and a sense "
            "of wonder at wildlife behavior, delivered like a wildlife YouTuber "
            "marveling at vivid detail as it happens, never a slow, hushed "
            "narration."
        ),
        "opening_hook": (
            "Open with a striking, specific image or animal behavior from "
            "beneath the surface, not a generic 'the ocean is vast' statement."
        ),
        "section_guidance": (
            "Cover the featured creature or ecosystem, how it survives and "
            "adapts, its role in the wider ecosystem, and one surprising or "
            "lesser-known behavior."
        ),
        "closing": "End by connecting the specific subject to the broader wonder and fragility of ocean life.",
    },
    Tone.reflective: {
        "style": (
            "Spiritual YouTube video. Ground abstract or introspective ideas in "
            "concrete traditions, practices, or personal experiences rather "
            "than abstract philosophy alone, delivered like a YouTuber pausing "
            "mid-video to think out loud with you, never a detached, monotone "
            "voiceover."
        ),
        "opening_hook": (
            "Open with a quiet, evocative moment or a timeless question that "
            "invites reflection."
        ),
        "section_guidance": (
            "Cover the origin of the practice or belief, how it is experienced "
            "today, what it offers those who follow it, and a broader "
            "universal takeaway."
        ),
        "closing": "End with a reflective, open-ended thought rather than a definitive conclusion.",
    },
    Tone.cinephile: {
        "style": (
            "Film YouTube video. Discuss films, scenes, and filmmaking techniques "
            "and their cultural impact without quoting dialogue verbatim or "
            "fabricating quotes attributed to real actors, directors, or other "
            "real people, delivered like a popular YouTube film critic firing "
            "off enthusiasm in rapid takes, never a slow academic lecture."
        ),
        "opening_hook": (
            "Open with a specific technique, moment, or piece of cultural impact "
            "worth examining, described in your own words rather than quoted."
        ),
        "section_guidance": (
            "Cover the film or scene's context, the technique or choice that "
            "makes it notable, its cultural or artistic impact, and how it "
            "influenced other films or audiences."
        ),
        "closing": "End by placing the specific example within the broader story of film as an art form.",
    },
    Tone.dynamic: {
        "style": (
            "Sports YouTube video. Favor high-energy, momentum-driven narration "
            "built around competition, effort, and achievement, delivered like "
            "a sports YouTuber hyping every highlight live, never a measured "
            "broadcast recap."
        ),
        "opening_hook": (
            "Open with a decisive moment of competition or a striking "
            "statistic, not a generic 'sports are popular' statement."
        ),
        "section_guidance": (
            "Cover the athlete, team, or event's background, the challenge or "
            "rivalry at stake, the pivotal moment of competition, and its "
            "lasting impact on the sport."
        ),
        "closing": "End by connecting the specific achievement to what it represents about human competition and perseverance.",
    },
    Tone.encouraging: {
        "style": (
            "Health and wellness YouTube video. Ground narration in practical, "
            "evidence-aware guidance rather than absolute medical claims -- "
            "prefer phrasing like 'many people find' or 'research suggests' "
            "over definitive prescriptions, delivered like a health YouTuber "
            "firing off advice you can use today, never a slow clinical "
            "rundown."
        ),
        "opening_hook": (
            "Open with a relatable everyday health challenge or a surprising, "
            "well-supported fact."
        ),
        "section_guidance": (
            "Cover the habit or topic itself, the evidence or reasoning behind "
            "it, practical ways to apply it, and common misconceptions or "
            "pitfalls."
        ),
        "closing": "End with a simple, actionable takeaway the viewer can start today.",
    },
    Tone.mysterious: {
        "style": (
            "Mystery/unexplained-discoveries YouTube video. Favor an atmosphere "
            "of intrigue -- present verified facts clearly, but frame open "
            "questions as genuinely open rather than implying a hidden "
            "conspiracy or a definitive secret answer, delivered like a "
            "true-crime YouTuber pulling you deeper into the case in real "
            "time, never a hushed, slow burn."
        ),
        "opening_hook": (
            "Open with the central unanswered question or the strangest known "
            "fact, before providing any context."
        ),
        "section_guidance": (
            "Cover what was found or observed, the leading scientific or "
            "scholarly explanations, why it remains unresolved or disputed, "
            "and what would settle the question."
        ),
        "closing": "End by leaving the central mystery open rather than manufacturing a false resolution.",
    },
    Tone.motivational: {
        "style": (
            "Personal development YouTube video. Ground abstract advice in "
            "concrete stories, research, or step-by-step practices rather "
            "than generic platitudes, delivered like a motivational YouTuber "
            "firing off advice you can act on right now, never a slow, "
            "measured pep talk."
        ),
        "opening_hook": (
            "Open with a relatable struggle or a specific, surprising "
            "insight, not a generic 'we all want to grow' statement."
        ),
        "section_guidance": (
            "Cover the core idea or skill, the reasoning or research behind "
            "it, a concrete way to practice it, and a common obstacle people "
            "face applying it."
        ),
        "closing": "End with a direct, actionable call to apply one specific idea from the video.",
    },
    Tone.savory: {
        "style": (
            "Food and culinary YouTube video. Ground the narration in sensory, "
            "appetizing detail (taste, aroma, texture) and the cultural "
            "stories behind a dish or cuisine, delivered like a food YouTuber "
            "devouring the moment on camera, never a slow, lingering food-doc "
            "narration."
        ),
        "opening_hook": (
            "Open with a vivid sensory moment -- a specific smell, taste, or "
            "the sizzle of cooking -- not a generic 'food is important' "
            "statement."
        ),
        "section_guidance": (
            "Cover the dish or cuisine's origin, what makes it distinctive, "
            "the people or techniques behind it, and its place in the "
            "culture today."
        ),
        "closing": "End by connecting the specific dish to the broader culture or tradition it comes from.",
    },
    Tone.majestic: {
        "style": (
            "Nature YouTube video. Favor sweeping, majestic imagery and a "
            "sense of scale in describing landscapes, wildlife, and natural "
            "phenomena, delivered like a landscape YouTuber reacting live to "
            "something vast, never a slow, reverent pan."
        ),
        "opening_hook": (
            "Open with a striking natural image or moment, not a generic "
            "'nature is beautiful' statement."
        ),
        "section_guidance": (
            "Cover the featured landscape or phenomenon, how it formed or "
            "functions, its role in the wider ecosystem, and why it matters "
            "to protect."
        ),
        "closing": "End by connecting the specific place or species to the broader fragility and grandeur of the natural world.",
    },
    Tone.gripping: {
        "style": (
            "Premium, high-production-value YouTube video style. Favor a "
            "suspenseful, cliffhanger-driven structure with escalating "
            "stakes, regardless of subject matter -- never fabricate claims "
            "about real people or events to heighten drama. Delivered like a "
            "thriller YouTuber racing toward the big reveal, never a slow, "
            "withholding prestige-doc pace."
        ),
        "opening_hook": (
            "Open with a striking, specific unanswered question or moment "
            "of tension that withholds the full picture to pull the viewer "
            "in."
        ),
        "section_guidance": (
            "Cover the central hook or conflict, escalating revelations "
            "building tension scene by scene, a credible turn or twist, and "
            "the stakes of the outcome."
        ),
        "closing": "End on a resonant, open note that lingers rather than a tidy, fully-resolved conclusion.",
    },
    # "Bao" planı (kullanıcı onaylı): KASITLI İSTİSNA -- her diğer tone
    # yukarıda "fast-paced, never slow" diye yazılmış (gece oturumu,
    # YouTube-dynamic temizliği). Bu tone o kuralı BİLEREK ihlal ediyor:
    # hedef kitle 3-8 yaş, ve hızlı kesmeler/yoğun tempo bu yaş grubu için
    # ZARARLI (aşırı uyarım, takip edememe) -- bkz. child_safe_guidance
    # (script_generator.py) ve docs/future-work.md'nin kids-mode uyarısı.
    Tone.nurturing: {
        "style": (
            "Gentle children's YouTube video (ages 3-8), in the warm, slow, "
            "reassuring style of shows like Bluey or Ms. Rachel. Favor a "
            "calm, unhurried pace with simple repetition and clear pauses -- "
            "the OPPOSITE of a fast-cut, high-energy YouTuber delivery -- "
            "so a young child can follow every beat."
        ),
        "opening_hook": (
            "Open with a warm, simple greeting to the character's everyday "
            "world -- a familiar, cozy moment, not a dramatic or urgent one."
        ),
        "section_guidance": (
            "Cover a small, relatable everyday situation, the character's "
            "simple feeling or challenge, a gentle choice guided by the "
            "episode's value (kindness, friendship, sharing, patience, or "
            "courage), and a warm, clear resolution."
        ),
        "closing": (
            "End with the value stated plainly and warmly, and a gentle, "
            "friendly invitation to join the character again next time."
        ),
    },
}


def get_template(tone: Tone | None) -> dict:
    return PROFILE_PROMPTS.get(tone, PROFILE_PROMPTS[Tone.credibility])
