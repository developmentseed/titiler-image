"""Common response models."""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, root_validator

from titiler.image.settings import iiif_settings


class IIIFProfileEnum(str, Enum):
    """Highest compliance level which is fully supported by the service. The value must be one of level0, level1, or level2."""

    level0 = "level0"
    level1 = "level1"
    level2 = "level2"


class IIIFSize(BaseModel):
    """
    IIIF Size info

    e.g. `{ "width": 150, "height": 100 }`

    Ref: https://iiif.io/api/image/3.0/#53-sizes
    """

    type: str = Field(default="Size", const=True)
    width: int
    height: int


class IIIFTile(BaseModel):
    """
    IIIF Tile info

    e.g `{ "width": 512, "height": 512, "scaleFactors": [ 1, 2, 4, 8, 16 ] }`

    Ref: https://iiif.io/api/image/3.0/#54-tiles
    """

    type: str = Field(default="Tile", const=True)
    scaleFactors: List[int]
    width: int
    height: Optional[int]

    @root_validator
    def check_height(cls, values):
        """Check height configuration."""
        if values.get("height", None):
            values["height"] = values["width"]

        return values


class iiifInfo(BaseModel):
    """
    IIIF Info model.

    Based on https://iiif.io/api/image/3.0/#5-image-information

    """

    # The @context tells Linked Data processors how to interpret the image information. If extensions are used then their context definitions should be included in this top-level @context property.
    context: str = Field(
        default="http://iiif.io/api/image/3/context.json", alias="@context", const=True
    )
    # The base URI of the image as defined in URI Syntax, including scheme, server, prefix and identifier without a trailing slash.
    id: str
    # The type for the Image API. The value must be the string ImageService3.
    type: str = Field(default="ImageService3", const=True)
    # The URI http://iiif.io/api/image which can be used to determine that the document describes an image service which is a version of the IIIF Image API.
    protocol: str = Field(default="http://iiif.io/api/image", const=True)
    # A string indicating the highest compliance level which is fully supported by the service. The value must be one of level0, level1, or level2.
    profile: IIIFProfileEnum = IIIFProfileEnum.level2
    # The width in pixels of the full image, given as an integer.
    width: int
    # The height in pixels of the full image, given as an integer.
    height: int
    # The maximum width in pixels supported for this image.
    maxWidth: Optional[int] = iiif_settings.maxWidth
    # The maximum height in pixels supported for this image.
    maxHeight: Optional[int] = iiif_settings.maxHeight
    # The maximum area in pixels supported for this image.
    maxArea: Optional[int] = iiif_settings.maxArea

    preferredFormats: Optional[List[str]] = ["png", "jpeg", "webp", "tif", "jp2"]

    # sizes property, which is used to describe preferred height and width combinations for representations of the full image.
    sizes: Optional[List[IIIFSize]]

    # tiles property which describes a set of image regions that have a consistent height and width, over a series of resolutions, that can be stitched together visually.
    tiles: Optional[List[IIIFTile]]

    # The rights property has the same semantics and requirements as it does in the Presentation API.
    rights: Optional[str]

    # https://iiif.io/api/image/3.0/#57-extra-functionality
    # An array of strings that can be used as the quality parameter, in addition to default.
    extraQualities: Optional[List[str]]
    # An array of strings that can be used as the format parameter, in addition to the ones specified in the referenced profile.
    extraFormats: Optional[List[str]]
    # An array of strings identifying features supported by the service, in addition to the ones specified in the referenced profile.
    extraFeatures: Optional[List[str]]

    # https://iiif.io/api/image/3.0/#58-linking-properties
    # TODO: Define models
    partOf: Optional[Dict]
    seeAlso: Optional[Dict]
    service: Optional[Dict]

    class Config:
        """IIIF Info model configuration."""

        use_enum_values = True
