from pydantic import BaseModel, Field

from app.config.profile_dimensions import Format, Pacing, Tone, TopicCategory
from app.models.asset import AssetPlan
from app.models.audio import AudioPlan
from app.models.character import CharacterReference
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
    # "Bao" planı (kullanıcı onaylı): topic_category/tone/format ile AYNI
    # yerde, AYNI desende -- stage 1'de bir kez çözülüp asset_generator ve
    # ai_video_generator'a parametre olarak geçiyor. character_reference ve
    # format == Format.kids BİLİNÇLİ OLARAK BİRBİRİNDEN BAĞIMSIZ (Tone/Format
    # gibi ortogonal iki boyut) -- karakter tutarlılığı, kids-güvenliği
    # olmadan da (veya tam tersi) teorik olarak kullanılabilir.
    character_reference: CharacterReference | None = None

    voice_name: str = ""
    voice_rate: float = 1.0
    voice_volume: float = 1.0
    video_source: str = "pexels"
    video_aspect: str = "9:16"  # VideoAspect value, e.g. "9:16", "16:9", "1:1"
    # ÖZELLİK A (kullanıcı onaylı, edit-script-and-re-render): run_pipeline()
    # zaten bu ikisini video_renderer.build_video_params()'a geçiriyordu ama
    # hiç projeye yazmıyordu -- script düzenlendikten sonra SADECE stage
    # 9-12'yi tekrar çalıştıran regenerate_from_edited_script()'in orijinal
    # BGM ayarlarını (varsayılana sessizce dönmeden) yeniden üretebilmesi
    # için burada saklanıyor.
    bgm_type: str = "random"
    bgm_volume: float = 0.2
    # GÖREV 6 (gece oturumu): "elevenlabs" bgm_type'ının kendi ayarı --
    # aynı ÖZELLİK A gerekçesiyle burada saklanıyor, regenerate_from_edited_
    # script() de ElevenLabs BGM'i (dosya değil, PROMPT'tan) yeniden
    # üretebilsin diye.
    video_music_prompt: str = ""
    # GÖREV F (kullanıcı onaylı): kullanıcının script_generator'a giden ek
    # stil rehberliğini/talimatlarını belirtebilmesi -- boş string "ek stil
    # rehberliği yok" anlamına gelir. ADDITIVE: script_generator'ın
    # DEFAULT_SCRIPT_SYSTEM_PROMPT'unun (no markdown/scene labels vb.) YERİNE
    # geçmez, onun yanına eklenir (kullanıcı bulgusuyla düzeltildi -- eskiden
    # tam bir override'dı, zararsız bir stil isteği bile formatı koruyan
    # talimatları sessizce silebiliyordu). Sadece kayıt/şeffaflık için
    # projede saklanıyor, run_pipeline() zaten bunları doğrudan alıyor.
    custom_system_prompt: str = ""
    custom_requirements: str = ""

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
    # "4 varyant" planı (kullanıcı onaylı): C/D, A/B ile AYNI desende (best-
    # effort, "" if skipped/failed) -- sadece farklı bir sabit zaman noktası.
    # See generate_thumbnail_variant_c/d.
    thumbnail_variant_c_path: str = ""
    thumbnail_variant_d_path: str = ""
    # Never set automatically -- publishing is a public, hard-to-reverse
    # action, so it's only populated after an explicit user-triggered call to
    # app.departments.growth.publisher.publish_project (see webui's Publish
    # section). None means "not published (yet)", not "publish failed".
    publish_result: PublishResult | None = None
    # ÖZELLİK B (kullanıcı onaylı): serbest, kullanıcı tanımlı etiketler --
    # playlist tarzı kanal-içi organizasyon için, SEO hashtags/keywords ile
    # KARIŞTIRILMAMALI (platformda keşfedilebilirlikle ilgisi yok). run_pipeline()
    # bunu hiç doldurmuyor -- sadece webui'nin _render_custom_tags_section()'ı
    # üzerinden, üretim sonrası kullanıcı tarafından ekleniyor.
    custom_tags: list[str] = Field(default_factory=list)
