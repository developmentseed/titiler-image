"""Titiler.image Enums."""

from enum import Enum
from types import DynamicClassAttribute

from rio_tiler.profiles import img_profiles

from titiler.core.resources.enums import ImageDriver, MediaType


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
