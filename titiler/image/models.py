"""Common response models."""

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated

from titiler.image.settings import iiif_settings


class IIIFSize(BaseModel):
    """
    IIIF Size info

    e.g. `{ "width": 150, "height": 100 }`

    Ref: https://iiif.io/api/image/3.0/#53-sizes
    """

    type: Literal["Size"] = "Size"
    width: int
    height: int


class IIIFTile(BaseModel):
    """
    IIIF Tile info

    e.g `{ "width": 512, "height": 512, "scaleFactors": [ 1, 2, 4, 8, 16 ] }`

    Ref: https://iiif.io/api/image/3.0/#54-tiles
    """

    type: Literal["Tile"] = "Tile"
    scaleFactors: List[int]
    width: int
    height: Optional[int] = None

    @model_validator(mode="before")
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
    context: Annotated[
        Literal["http://iiif.io/api/image/3/context.json"],
        Field(alias="@context"),
    ] = "http://iiif.io/api/image/3/context.json"

    # The base URI of the image as defined in URI Syntax, including scheme, server, prefix and identifier without a trailing slash.
    id: str

    # The type for the Image API. The value must be the string ImageService3.
    type: Literal["ImageService3"] = "ImageService3"

    # The URI http://iiif.io/api/image which can be used to determine that the document describes an image service which is a version of the IIIF Image API.
    protocol: Literal["http://iiif.io/api/image"] = "http://iiif.io/api/image"
    # A string indicating the highest compliance level which is fully supported by the service. The value must be one of level0, level1, or level2.
    profile: Literal["level0", "level1", "level2"] = "level2"
    # The width in pixels of the full image, given as an integer.
    width: int
    # The height in pixels of the full image, given as an integer.
    height: int
    # The maximum width in pixels supported for this image.
    maxWidth: Optional[int] = iiif_settings.max_width
    # The maximum height in pixels supported for this image.
    maxHeight: Optional[int] = iiif_settings.max_height
    # The maximum area in pixels supported for this image.
    maxArea: Optional[int] = iiif_settings.max_area

    preferredFormats: Optional[List[str]] = ["png", "jpeg", "webp", "tif", "jp2"]

    # sizes property, which is used to describe preferred height and width combinations for representations of the full image.
    sizes: Optional[List[IIIFSize]] = None

    # tiles property which describes a set of image regions that have a consistent height and width, over a series of resolutions, that can be stitched together visually.
    tiles: Optional[List[IIIFTile]] = None

    # The rights property has the same semantics and requirements as it does in the Presentation API.
    rights: Optional[str] = None

    # https://iiif.io/api/image/3.0/#57-extra-functionality
    # An array of strings that can be used as the quality parameter, in addition to default.
    extraQualities: Optional[List[str]] = None
    # An array of strings that can be used as the format parameter, in addition to the ones specified in the referenced profile.
    extraFormats: Optional[List[str]] = None
    # An array of strings identifying features supported by the service, in addition to the ones specified in the referenced profile.
    extraFeatures: Optional[List[str]] = None

    # https://iiif.io/api/image/3.0/#58-linking-properties
    # TODO: Define models
    partOf: Optional[Dict] = None
    seeAlso: Optional[Dict] = None
    service: Optional[Dict] = None
