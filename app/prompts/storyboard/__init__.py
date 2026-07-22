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
        "Favor human-centered footage: close-ups of faces and expressions, "
        "everyday life scenarios, and abstract/conceptual visuals."
    ),
}


def get_shot_guidance(category: TopicCategory | None) -> str:
    return SHOT_GUIDANCE.get(category, SHOT_GUIDANCE[TopicCategory.history])
