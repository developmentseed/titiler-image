"""API settings."""

from typing import Optional

import pydantic


class ApiSettings(pydantic.BaseSettings):
    """API settings"""

    name: str = "titiler-image"
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"

    @pydantic.validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    class Config:
        """model config"""

        env_prefix = "TITILER_IMAGE_API_"
        env_file = ".env"


class IIIFSettings(pydantic.BaseSettings):
    """IIIF settings"""

    # The maximum width in pixels supported for this image.
    maxWidth: Optional[int]
    # The maximum height in pixels supported for this image.
    maxHeight: Optional[int]
    # The maximum area in pixels supported for this image.
    maxArea: Optional[int]

    @pydantic.root_validator
    def check_max(cls, values):
        """Check MaxWitdh and MaxHeight configuration."""
        # maxWidth must be specified if maxHeight is specified.
        keys = {"maxWidth", "maxHeight"}
        if keys.intersection(values):
            if "maxWidth" not in values:
                raise Exception("maxWidth has to be set if maxHeight is.")
            if "maxHeight" not in values:
                values["maxHeight"] = values["maxWidth"]

        return values

    class Config:
        """model config"""

        env_prefix = "TITILER_IMAGE_IIIF_"
        env_file = ".env"


iiif_settings = IIIFSettings()
api_settings = ApiSettings()
