"""Titiler.image Enums."""

from enum import Enum
from types import DynamicClassAttribute

from rio_tiler.profiles import img_profiles

from titiler.core.resources.enums import ImageDriver, MediaType


class IIIFQuality(str, Enum):
    """Image quality.

    ref: https://iiif.io/api/image/3.0/#quality
    """

    # The image is returned with all of its color information.
    color = "color"
    # The image is returned in grayscale, where each pixel is black, white or any shade of gray in between.
    gray = "gray"
    # The image returned is bitonal, where each pixel is either black or white.
    bitonal = "bitonal"
    # The image is returned using the server’s default quality (e.g. color, gray or bitonal) for the image.
    default = "default"


class IIIFImageFormat(str, Enum):
    """Available Output image type."""

    jpg = "jpg"
    tif = "tif"
    png = "png"
    gif = "gif"
    jp2 = "jp2"
    # pdf = "pdf" Not Available

    @DynamicClassAttribute
    def profile(self):
        """Return rio-tiler image default profile."""
        return img_profiles.get(self._name_, {})

    @DynamicClassAttribute
    def driver(self):
        """Return rio-tiler image default profile."""
        return ImageDriver[self._name_].value

    @DynamicClassAttribute
    def mediatype(self):
        """Return image media type."""
        return MediaType[self._name_].value
