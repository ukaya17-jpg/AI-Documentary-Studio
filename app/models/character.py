from pydantic import BaseModel, Field, model_validator


class CharacterReference(BaseModel):
    """A recurring character's reference images, threaded through the pipeline
    to Kling O1 Reference-to-Video (see docs/character-consistency-research.md).

    Maps directly onto that model's `elements[]` entry shape
    (`OmniVideoElementInput`): `frontal_image_url` is the required main view,
    `reference_image_urls` are 1-3 additional angles. `name` is only used to
    build the `@Element1` prompt prefix (see asset_generator.build_asset_plan)
    -- it is never sent to the API itself.

    BUG FIX (kullanıcı bildirdi, 2026-08-15): fal.ai'nin GERÇEK O1 şeması
    `reference_image_urls` için "array of 1-3 additional images" istiyor --
    yani EN AZ 1 zorunlu, boş liste GEÇERSİZ. app.config.locations'ın
    tek-açı (front.jpg only) mekanları bu alanı BOŞ bırakıyordu ->
    fal.ai her seferinde 422 Unprocessable Entity ile reddediyordu (bir
    karakter/mekan içeren HER sahne, istisnasız). Bu model_validator, tek
    bir merkezi noktada (locations.py/characters.py'nin HER ikisini de
    kapsayacak şekilde) reference_image_urls boş kalırsa frontal_image_url'i
    kendisiyle doldurur -- API'ye her zaman en az 1 ek görsel gitmesini
    garanti eder, gerçek bir ek açı olmasa bile (fal.ai'nin kabul ettiği,
    zararsız bir tekrar). model_validator(mode="after") kullanılıyor --
    field_validator DEĞİL, çünkü pydantic v2 varsayılan (default_factory)
    değerlerde field_validator'ı ÇALIŞTIRMIYOR (validate_default=True
    gerekir); bu yüzden ilk denemede sessizce hiç tetiklenmemişti.
    """

    name: str = ""
    frontal_image_url: str
    reference_image_urls: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ensure_at_least_one_reference_image(self):
        if not self.reference_image_urls and self.frontal_image_url:
            self.reference_image_urls = [self.frontal_image_url]
        return self
