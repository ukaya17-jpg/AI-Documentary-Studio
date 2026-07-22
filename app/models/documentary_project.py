from pydantic import BaseModel

from app.config.profile_dimensions import Pacing, TopicCategory
from app.models.asset import AssetPlan
from app.models.audio import AudioPlan
from app.models.outline import Outline
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
