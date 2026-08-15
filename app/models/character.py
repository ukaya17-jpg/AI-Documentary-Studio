import base64
import io

from PIL import Image
from pydantic import BaseModel, Field, model_validator

# fal.ai Kling O1's real, empirically-confirmed elements[].reference_image_urls
# constraints -- discovered the hard way across two separate 422 waves
# (2026-08-15): 01a005fc ("Image dimensions are too small. Minimum
# dimensions are 300x300 pixels.") and, after fixing only the size, 01a0062e
# ("The aspect ratio of the image should be between 0.4 and 2.5.") on the
# SAME two characters (Luna/Professor Nova, cropped 275x768 by Google Flow).
# Both constraints are checked here, once, at CharacterReference construction
# time (covers characters.py AND locations.py, the two callers) so a badly
# exported/cropped asset fails LOUD the moment it's read from disk -- not
# expensively, minutes later, via a wasted fal.ai job that only reports the
# real error on get_job_result.
_MIN_DIMENSION = 300
_MIN_ASPECT_RATIO = 0.4
_MAX_ASPECT_RATIO = 2.5


def _check_reference_image_dimensions(data_uri: str, label: str) -> None:
    if not data_uri.startswith("data:image/"):
        return  # remote URL -- can't inspect pixel dimensions without a network call
    try:
        _header, encoded = data_uri.split(",", 1)
        with Image.open(io.BytesIO(base64.b64decode(encoded))) as im:
            width, height = im.size
    except Exception:
        return  # not a decodable image (e.g. a unit-test placeholder) -- nothing to check
    if width < _MIN_DIMENSION or height < _MIN_DIMENSION:
        raise ValueError(
            f"{label}: {width}x{height} is smaller than fal.ai's "
            f"{_MIN_DIMENSION}x{_MIN_DIMENSION} minimum for Kling O1 reference images"
        )
    ratio = width / height
    if not (_MIN_ASPECT_RATIO <= ratio <= _MAX_ASPECT_RATIO):
        raise ValueError(
            f"{label}: {width}x{height} has aspect ratio {ratio:.3f}, outside fal.ai's "
            f"{_MIN_ASPECT_RATIO}-{_MAX_ASPECT_RATIO} range for Kling O1 reference images"
        )


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

    @model_validator(mode="after")
    def _validate_reference_image_dimensions(self):
        label = self.name or "reference"
        _check_reference_image_dimensions(self.frontal_image_url, f"{label}.frontal_image_url")
        for i, url in enumerate(self.reference_image_urls):
            _check_reference_image_dimensions(url, f"{label}.reference_image_urls[{i}]")
        return self
