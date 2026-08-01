from pydantic import BaseModel, Field


class CharacterReference(BaseModel):
    """A recurring character's reference images, threaded through the pipeline
    to Kling O1 Reference-to-Video (see docs/character-consistency-research.md).

    Maps directly onto that model's `elements[]` entry shape
    (`OmniVideoElementInput`): `frontal_image_url` is the required main view,
    `reference_image_urls` are 1-3 additional angles. `name` is only used to
    build the `@Element1` prompt prefix (see asset_generator.build_asset_plan)
    -- it is never sent to the API itself.
    """

    name: str = ""
    frontal_image_url: str
    reference_image_urls: list[str] = Field(default_factory=list)
