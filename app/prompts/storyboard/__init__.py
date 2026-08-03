"""Per-category visual/shot guidance for the storyboard stage."""

from app.config.profile_dimensions import TopicCategory

SHOT_GUIDANCE = {
    TopicCategory.travel: (
        "Favor wide establishing shots of landscapes and cityscapes, street-level "
        "detail shots of food and daily life, and aerial/drone-style shots."
    ),
    TopicCategory.history: (
        "Favor archival-style imagery: old maps, monuments, ruins, statues, "
        "and landscapes evoking the period."
    ),
    TopicCategory.space: (
        "Favor space and astronomy stock footage: starfields, planets, rockets, "
        "telescopes, and night-sky timelapses."
    ),
    TopicCategory.psychology: (
        "Favor human-centered footage: close-ups of faces and expressions "
        "showing real emotional reactions, people making real decisions in "
        "everyday settings (shopping, working, weighing a choice), and "
        "research-adjacent imagery (note-taking, charts, lab or study "
        "settings). Avoid mystical, spiritual, or new-age imagery (candles, "
        "crystals, zodiac charts, incense) and vague decorative objects -- "
        "every shot should read as a real, filmable psychological or "
        "behavioral moment, not a mood-board metaphor."
    ),
    TopicCategory.marine: (
        "Favor underwater cinematography: coral reefs, marine animals (fish, "
        "whales, dolphins, sharks), light rays through water, and wide ocean "
        "or coastline establishing shots."
    ),
    TopicCategory.spiritual: (
        "Favor serene, contemplative footage: temples, monasteries, meditation "
        "and nature scenes, candlelight, and quiet human moments of reflection."
    ),
    TopicCategory.film_highlights: (
        "Favor cinema-adjacent b-roll: film reels, cinemas and projectors, "
        "behind-the-scenes/set imagery, clapperboards, and film festival or "
        "awards imagery -- avoid search terms implying use of actual "
        "copyrighted film footage."
    ),
    TopicCategory.sports: (
        "Favor dynamic sports footage: athletes in motion, stadiums and "
        "crowds, close-ups of effort and celebration, and slow-motion-style "
        "action shots."
    ),
    TopicCategory.healthy_living: (
        "Favor everyday wellness footage: exercise and movement, healthy food "
        "preparation, nature/outdoor activity, and calm indoor lifestyle "
        "scenes."
    ),
    TopicCategory.mysterious_discoveries: (
        "Favor atmospheric, intriguing footage: archaeological or exploration "
        "sites, dim lighting and shadows, close-ups of artifacts or "
        "documents, and vast unexplored landscapes."
    ),
    TopicCategory.personal_development: (
        "Favor human-centered, aspirational footage: people working, "
        "studying, or practicing a skill, journaling or planning, and "
        "everyday environments (home, office, gym). Keep 'quiet focused "
        "moments' concrete and secular -- a person writing at a desk, "
        "reviewing notes, or pausing mid-task -- not meditation, yoga, or "
        "spiritual/mystical decor (candles, crystals, zen ornaments), which "
        "belong to the spiritual category, not this one."
    ),
    TopicCategory.food_culture: (
        "Favor close-up culinary footage: food preparation, cooking "
        "techniques, plating, ingredients, and bustling kitchens or markets."
    ),
    TopicCategory.nature: (
        "Favor sweeping nature footage: landscapes, forests, mountains, "
        "wildlife in their habitat, and weather or seasonal timelapses."
    ),
    TopicCategory.netflix_style: (
        "Favor moody, high-contrast footage: dim interiors, close-ups with "
        "shallow depth of field, slow push-ins, and atmospheric night or "
        "low-light scenes -- avoid search terms referencing any specific "
        "streaming platform or real production by name."
    ),
    TopicCategory.values_education: (
        "Favor warm, simple, everyday scenes centered on the recurring "
        "character: bright daylight settings (a garden, a park, a cozy "
        "room), soft rounded shapes, gentle character expressions and "
        "small friendly gestures -- never dim lighting, shadows, or "
        "tense/dramatic framing."
    ),
}


def get_shot_guidance(category: TopicCategory | None) -> str:
    return SHOT_GUIDANCE.get(category, SHOT_GUIDANCE[TopicCategory.history])
