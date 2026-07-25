"""Outline templates per Tone.

Each template is a plain dict of guidance strings plugged into the outline
generation prompt: how to open the documentary, what kind of sections to
favor, and how to close. ``PROFILE_PROMPTS`` keys mirror
``app.config.profile_dimensions.Tone`` values.

Previously keyed directly by ``TopicCategory`` (one hard-locked tone per
category); re-keyed by ``Tone`` so a topic's tone can be resolved
independently of its category (see ``resolve_tone``). The template content
itself is unchanged -- each category's former slot now sits under that
category's default tone (travel->cinematic, history->credibility,
space->epic, psychology->scientific), so resolving with no override
reproduces the exact same prompt text as before.
"""

from app.config.profile_dimensions import Tone

PROFILE_PROMPTS = {
    Tone.cinematic: {
        "style": (
            "Travel documentary. Ground the narration in concrete sensory detail "
            "(sights, sounds, food, local life) and a strong sense of place."
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
            "History documentary. Prioritize chronological or cause-effect clarity "
            "and named people, dates, and turning points."
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
            "Space/science documentary. Favor scale, precision, and awe; translate "
            "technical facts into vivid comparisons a general audience can grasp."
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
            "Psychology documentary. Ground abstract concepts in a relatable "
            "scenario or experiment before generalizing."
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
            "Marine/nature documentary. Ground the narration in vivid sensory "
            "detail of the underwater world (light, motion, scale) and a sense "
            "of wonder at wildlife behavior."
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
            "Spiritual documentary. Ground abstract or introspective ideas in "
            "concrete traditions, practices, or personal experiences rather "
            "than abstract philosophy alone."
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
            "Film documentary. Discuss films, scenes, and filmmaking techniques "
            "and their cultural impact without quoting dialogue verbatim or "
            "fabricating quotes attributed to real actors, directors, or other "
            "real people."
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
            "Sports documentary. Favor high-energy, momentum-driven narration "
            "built around competition, effort, and achievement."
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
}


def get_template(tone: Tone | None) -> dict:
    return PROFILE_PROMPTS.get(tone, PROFILE_PROMPTS[Tone.credibility])
