"""SEO stage: title/description/hashtags, chapters, and engagement suggestions
for the finished documentary.

Reuses the existing app.services.llm.generate_social_metadata() (with its
own retry + heuristic-fallback behavior) for title/description/hashtags
instead of writing a new prompt.

chapters/end_screen_suggestion/pinned_comment are creator-facing advisory
metadata, not automated platform actions -- this pipeline's primary output
is short vertical video (YouTube Shorts/TikTok/Reels format), and YouTube
chapters + end screens are formally long-form-only features. Chapters are
still computed (deterministically, no LLM cost) since they become useful if
a longer-form video is ever produced from the same pipeline; a pinned
comment suggestion applies to Shorts too.
"""

from loguru import logger

from app.models.scene import ScenePlan
from app.models.script import Script
from app.models.seo import SeoMetadata
from app.services import llm
from app.services.documentary_llm_utils import generate_json


def generate_chapters(scene_plan: ScenePlan | None) -> list[str]:
    if not scene_plan or not scene_plan.scenes:
        return []
    chapters = []
    elapsed = 0.0
    for scene in scene_plan.scenes:
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        chapters.append(f"{minutes}:{seconds:02d} {scene.title}")
        elapsed += scene.duration_seconds
    return chapters


def build_engagement_prompt(
    topic: str,
    script: Script,
    language: str = "",
    existing_title: str = "",
    key_facts: list[str] | None = None,
) -> str:
    # OTONOM KARAR (GÖREV 2, SEO Engine genişletmesi): title_variants/keywords
    # bilinçli olarak burada, MEVCUT engagement çağrısına eklendi --
    # llm.generate_social_metadata()/build_social_metadata_prompt() (legacy
    # tekil-video pipeline'ıyla PAYLAŞILAN kod) hiç değiştirilmedi, yeni bir
    # LLM çağrısı da eklenmedi. Yeni ücretli bir API/arama-hacmi
    # entegrasyonu yok -- tamamen aynı $0 ek maliyetli LLM çağrısının
    # döndürdüğü JSON şemasının genişletilmesi.
    prompt = (
        "You are a YouTube/social growth assistant. For the documentary below, "
        "suggest a short end-of-video note for the creator, a pinned comment "
        "to drive engagement, alternative title ideas, and broader SEO keywords."
        f'\n\nTopic: "{topic}"\n\nNarration:\n{script.full_text}'
    )
    # OTONOM KARAR (yüzyıl/binyıl grounding düzeltmesi): storyboard'daki
    # topic+key_facts[:3] deseniyle tutarlı -- script anlatımı sayısal bir
    # zaman ölçeğini hiç vermeyebiliyor (bilinçli olarak şiirsel/genel
    # kalabiliyor), araştırma aşamasında doğrulanmış facts burada olmazsa bu
    # çağrı da script kadar belirsiz kalır.
    facts = [str(f).strip() for f in (key_facts or []) if f and str(f).strip()]
    if facts:
        facts_lines = "\n".join(f"- {fact}" for fact in facts)
        prompt += (
            f"\n\nVerified facts:\n{facts_lines}\n"
            "Verify time-scale words (e.g. \"century\" vs \"millennium\" vs "
            "\"decade\") against these facts before writing -- do not restate "
            "a different order of magnitude than what the facts establish."
        )
    if existing_title:
        # OTONOM KARAR (gerçek API doğrulamasında bulundu): title ve
        # title_variants iki AYRI LLM çağrısından geliyor (generate_social_
        # metadata / generate_engagement_metadata) -- ikinci çağrı birincinin
        # sonucunu görmeden "alternatif" başlık üretirse, tesadüfen ana
        # başlıkla birebir aynı bir sonuç üretebiliyor (gözlemlendi). Buraya
        # ana başlığı açıkça vermek yeni bir LLM çağrısı EKLEMİYOR, sadece
        # zaten yapılan bu çağrının bağlamını zenginleştiriyor.
        prompt += f'\n\nThe video\'s main title is already: "{existing_title}"'
    if language and language != "auto":
        prompt += f"\n\nRespond in language: {language}"
    prompt += """

Respond with a single JSON object with exactly this shape:
{"end_screen_suggestion": "...", "pinned_comment": "...", "title_variants": ["...", "..."], "keywords": ["...", "..."]}
end_screen_suggestion: one sentence telling the creator what to say/show in
the last few seconds (e.g., a subscribe prompt or a tease for a related
topic) -- advice for the creator, not on-screen text to render.
pinned_comment: a short, engaging comment (a question or a hook) the creator
can pin to drive replies.
title_variants: exactly 2 alternative titles for the same video, each taking
a different angle/hook than an obvious title would (for the creator to A/B
test) -- each must be genuinely different from the main title above and
from each other, not a minor reword of it.
keywords: 8 to 10 broader SEO keywords or short phrases relevant to the
topic (for the platform's tags/keywords field, not on-screen hashtags --
plain text, no "#" prefix, no duplicates).
Do not include any other text."""
    return prompt


def generate_engagement_metadata(
    topic: str,
    script: Script,
    language: str = "auto",
    existing_title: str = "",
    key_facts: list[str] | None = None,
) -> dict:
    try:
        data = generate_json(
            build_engagement_prompt(
                topic, script, language, existing_title, key_facts=key_facts
            )
        )
        return {
            "end_screen_suggestion": str(data.get("end_screen_suggestion", "")).strip(),
            "pinned_comment": str(data.get("pinned_comment", "")).strip(),
            "title_variants": [
                str(t).strip() for t in data.get("title_variants", []) if str(t).strip()
            ],
            "keywords": [
                str(k).strip() for k in data.get("keywords", []) if str(k).strip()
            ],
        }
    except Exception as e:
        logger.warning(f"seo_generator: engagement metadata generation failed: {e}")
        return {
            "end_screen_suggestion": "",
            "pinned_comment": "",
            "title_variants": [],
            "keywords": [],
        }


def generate_seo_metadata(
    topic: str,
    script: Script,
    language: str = "auto",
    platform: str = "youtube_shorts",
    scene_plan: ScenePlan | None = None,
    key_facts: list[str] | None = None,
) -> SeoMetadata:
    result = llm.generate_social_metadata(
        video_subject=topic,
        video_script=script.full_text,
        language=language,
        platform=platform,
        key_facts=key_facts,
    )
    engagement = generate_engagement_metadata(
        topic,
        script,
        language,
        existing_title=result.get("title", ""),
        key_facts=key_facts,
    )
    return SeoMetadata(
        title=result.get("title", ""),
        description=result.get("caption", ""),
        hashtags=list(result.get("hashtags", [])),
        chapters=generate_chapters(scene_plan),
        end_screen_suggestion=engagement["end_screen_suggestion"],
        pinned_comment=engagement["pinned_comment"],
        title_variants=engagement["title_variants"],
        keywords=engagement["keywords"],
    )
