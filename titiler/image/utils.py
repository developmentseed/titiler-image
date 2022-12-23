"""Titiler.image utility functions."""

import math
import typing

import numpy
from affine import Affine
from rasterio.warp import reproject
from rio_tiler.models import ImageData

from fastapi import HTTPException


def _percent(x: float, y: float) -> float:
    return (x / 100) * y


def _get_sizes(
    w: int,
    h: int,
    max_width: int = None,
    max_height: int = None,
    max_area: int = None,
) -> typing.Tuple[int, int]:
    """Return Output width/height constrained by environment."""
    # use size constraints if present, else full
    if max_area and max_area < (w * h):
        area_ratio = max_area / (w * h)
        w = int(w * area_ratio)
        h = int(h * area_ratio)

    elif max_width:
        max_height = max_height or max_width
        width, height = w, h

        if w > max_width:
            w = max_width
            h = int(height * max_width / width)

        if h > max_height:
            h = max_height
            w = int(width * max_height / height)

    return w, h


def rotate(img: ImageData, angle: float, expand: bool = False, mirrored: bool = False):
    """Rotate Image."""
    rotated_affine = Affine.rotation(angle, (img.width // 2, img.height // 2))

    nw = img.width
    nh = img.height

    # Adapted from https://github.com/python-pillow/Pillow/blob/acdb882aae391f29e551a09dc678b153c0c04e5b/src/PIL/Image.py#L2297-L2311
    if expand:
        xx = []
        yy = []
        for x, y in ((0, 0), (img.width, 0), (img.width, img.height), (0, img.height)):
            x, y = rotated_affine * (x, y)
            xx.append(x)
            yy.append(y)

        nw = math.ceil(max(xx)) - math.floor(min(xx))
        nh = math.ceil(max(yy)) - math.floor(min(yy))

        rotated_affine = rotated_affine * Affine.translation(
            -(nw - img.width) / 2.0, -(nh - img.height) / 2.0
        )

    # Rotate the data
    data = numpy.zeros((img.count, nh, nw), dtype=img.data.dtype)
    _ = reproject(
        numpy.flip(img.data, axis=2) if mirrored else img.data,
        data,
        src_crs="epsg:4326",  # Fake CRS
        src_transform=Affine.identity(),
        dst_crs="epsg:4326",  # Fake CRS
        dst_transform=rotated_affine,
    )

    # Rotate the mask
    mask = numpy.zeros((nh, nw), dtype=img.mask.dtype)
    _ = reproject(
        numpy.flip(img.mask, axis=1) if mirrored else img.mask,
        mask,
        src_crs="epsg:4326",  # Fake CRS
        src_transform=Affine.identity(),
        dst_crs="epsg:4326",  # Fake CRS
        dst_transform=rotated_affine,
    )

    return ImageData(
        data,
        mask,
        assets=img.assets,
        metadata=img.metadata,
        band_names=img.band_names,
        dataset_statistics=img.dataset_statistics,
    )


def image_to_grayscale(img: ImageData) -> ImageData:
    """Convert Image to Grayscale using ITU-R 601-2 luma transform."""
    if img.count == 1:
        return img

    if img.count == 3:
        data = (
            img.data[0] * 299 / 1000
            + img.data[1] * 587 / 1000
            + img.data[2] * 114 / 1000
        )
        return ImageData(
            data.astype("uint8"),
            img.mask,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=["b1"],
            metadata=img.metadata,
        )

    raise HTTPException(
        status_code=400,
        detail=f"Number of band {img.count} for grayscale transformation.",
    )


def image_to_bitonal(img: ImageData) -> ImageData:
    """Convert Image to Bitonal

    All values larger than 127 are set to 255 (white), all other values to 0 (black).
    """
    img = image_to_grayscale(img)
    return ImageData(
        numpy.where(img.data > 127, 255, 0).astype("uint8"),
        img.mask,
        assets=img.assets,
        crs=img.crs,
        bounds=img.bounds,
        band_names=["b1"],
        metadata=img.metadata,
    )
