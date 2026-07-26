from pydantic import BaseModel, Field


class SeoMetadata(BaseModel):
    title: str = ""
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
    # Creator-facing advisory metadata, not automated platform actions.
    # "MM:SS Title" markers -- only meaningful for a long-form upload, since
    # YouTube Shorts (this pipeline's primary output) don't support chapters.
    chapters: list[str] = Field(default_factory=list)
    end_screen_suggestion: str = ""
    pinned_comment: str = ""
    # GÖREV 2 (SEO Engine genişletmesi, OTONOM KARAR): mevcut engagement
    # LLM çağrısına eklendi, yeni bir çağrı/ücretli API yok. title_variants:
    # A/B test için ana başlığa alternatif 2 başlık. keywords: platformun
    # etiket/keywords alanı için ana hashtags listesinden daha geniş, "#"
    # önekisiz bir SEO anahtar kelime listesi.
    title_variants: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
