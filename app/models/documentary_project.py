from pydantic import BaseModel

from app.config.profile_dimensions import Format, Pacing, Tone, TopicCategory
from app.models.asset import AssetPlan
from app.models.audio import AudioPlan
from app.models.outline import Outline
from app.models.publish import PublishResult
from app.models.quality import QualityVerdict
from app.models.research_plan import ResearchPlan
from app.models.scene import ScenePlan
from app.models.script import Script
from app.models.seo import SeoMetadata
from app.models.storyboard import Storyboard
from app.models.timeline import Timeline


class DocumentaryProject(BaseModel):
    project_id: str
    topic: str
    language: str = "auto"
    topic_category: TopicCategory | None = None
    # Resolved once topic_category is known (see resolve_tone in
    # default_pipeline.run_pipeline); None only before stage 1 completes.
    tone: Tone | None = None
    # Unlike tone, format has no category-based default -- None means "no
    # format applied", not "not yet resolved" (see resolve_format).
    format: Format | None = None
    pacing: Pacing = Pacing.short

    voice_name: str = ""
    voice_rate: float = 1.0
    voice_volume: float = 1.0
    video_source: str = "pexels"
    video_aspect: str = "9:16"  # VideoAspect value, e.g. "9:16", "16:9", "1:1"

    research_plan: ResearchPlan | None = None
    outline: Outline | None = None
    scene_plan: ScenePlan | None = None
    script: Script | None = None
    storyboard: Storyboard | None = None
    asset_plan: AssetPlan | None = None
    audio_plan: AudioPlan | None = None
    timeline: Timeline | None = None
    seo: SeoMetadata | None = None

    final_video_path: str = ""
    # Informational only -- never gates final_video_path or blocks the
    # pipeline. See app.thinking.quality_critic.
    quality_verdict: QualityVerdict | None = None
    # Best-effort; "" when generation failed or was skipped. See
    # app.departments.growth.thumbnail_generator.
    thumbnail_path: str = ""
    # A second, distinct thumbnail choice (earlier frame, same title) for a
    # quick A/B compare -- best-effort like thumbnail_path, "" if skipped/
    # failed. See app.departments.growth.thumbnail_generator.generate_thumbnail_variant_b.
    thumbnail_variant_b_path: str = ""
    # Never set automatically -- publishing is a public, hard-to-reverse
    # action, so it's only populated after an explicit user-triggered call to
    # app.departments.growth.publisher.publish_project (see webui's Publish
    # section). None means "not published (yet)", not "publish failed".
    publish_result: PublishResult | None = None
