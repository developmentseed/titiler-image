"""API settings."""

from typing import Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    """API settings"""

    name: str = "titiler-image"
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    root_path: str = ""

    model_config = {
        "env_prefix": "TITILER_IMAGE_API_",
        "env_file": ".env",
        "extra": "ignore",
    }

    @field_validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]


class IIIFSettings(BaseSettings):
    """IIIF settings"""

    # The maximum width in pixels supported for this image.
    max_width: Optional[int] = None

    # The maximum height in pixels supported for this image.
    max_height: Optional[int] = None

    # The maximum area in pixels supported for this image.
    max_area: Optional[int] = None

    model_config = {
        "env_prefix": "TITILER_IMAGE_IIIF_",
        "env_file": ".env",
        "extra": "ignore",
    }

    @model_validator(mode="before")
    def check_max(cls, values):
        """Check MaxWitdh and MaxHeight configuration."""
        # maxWidth must be specified if maxHeight is specified.
        keys = {"max_width", "max_height"}
        if keys.intersection(values):
            if "max_width" not in values:
                raise Exception("max_width has to be set if max_height is.")
            if "max_height" not in values:
                values["max_height"] = values["max_width"]

        return values


iiif_settings = IIIFSettings()
api_settings = ApiSettings()
