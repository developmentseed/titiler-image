"""Test titiler-image utils."""

import os

import numpy
import pytest
from fastapi import HTTPException
from rio_tiler.io import ImageReader

from titiler.image.utils import image_to_bitonal, image_to_grayscale, rotate

PREFIX = os.path.join(os.path.dirname(__file__), "fixtures")
boston_jpeg = os.path.join(PREFIX, "boston_small.jpg")


def test_rotate():
    """test rotation."""
    with ImageReader(boston_jpeg) as src:
        # read part of the image with mask area
        img = src.part((-100, 100, 100, 0))
        assert img.array.mask[0, 0, 0]  # Masked
        assert not img.array.mask[0, 0, 100]  # Not Masked
        assert img.array.shape == (3, 100, 200)

        img0 = rotate(img, 0, expand=True)
        numpy.testing.assert_array_equal(img.data, img0.data)

        imgm = rotate(img, 0, mirrored=True)
        with numpy.testing.assert_raises(AssertionError):
            numpy.testing.assert_array_equal(imgm.data, img.data)

        img180 = rotate(img, 180, expand=True)
        with numpy.testing.assert_raises(AssertionError):
            numpy.testing.assert_array_equal(img180.data, img.data)

        assert img.data[0, 0, 100] == img180.data[0, 99, 99]
        assert not img180.array.mask[0, 0, 0]  # Not Masked
        assert img180.array.mask[0, 0, 100]  # Masked

        img90 = rotate(img, 90, expand=True)
        assert img90.array.shape == (3, 200, 100)
        assert img90.array.mask[0, 0, 0]  # Masked
        assert not img90.array.mask[0, 100, 0]  # Not Masked

        img90 = rotate(img, 90, expand=False)
        assert img90.array.shape == (3, 100, 200)
        assert img90.array.mask[0, 0, 0]  # Masked
        assert img90.array.mask[0, 0, 100]  # Masked
        assert img90.array.mask[0, 99, 0]  # Masked
        assert not img90.array.mask[0, 99, 100]  # not Masked

        img125 = rotate(img, 125, expand=True)
        assert img125.array.shape == (3, 222, 198)
        assert img125.array.mask[0, 0, 0]  # Masked
        assert not img125.array.mask[0, 150, 50]  # Not Masked


def test_gray():
    """test to_grayscale."""
    with ImageReader(boston_jpeg) as src:
        img = src.preview()
        assert img.array.shape == (3, 695, 1000)
        assert img.array.dtype == "uint8"

        grey = image_to_grayscale(img)
        assert grey.array.shape == (1, 695, 1000)
        assert grey.array.dtype == "uint8"

        img = src.preview(indexes=1)
        assert img.array.shape == (1, 695, 1000)
        grey = image_to_grayscale(img)
        numpy.testing.assert_array_equal(img.data, grey.data)

        with pytest.raises(HTTPException):
            img = src.preview(indexes=(1, 1, 1, 1))
            image_to_grayscale(img)


def test_bitonal():
    """test to_bitonal."""
    with ImageReader(boston_jpeg) as src:
        img = src.preview()
        assert img.array.shape == (3, 695, 1000)
        assert img.array.dtype == "uint8"

        grey = image_to_bitonal(img)
        assert grey.array.shape == (1, 695, 1000)
        assert grey.array.dtype == "uint8"
        assert numpy.unique(grey.array).tolist() == [0, 255]
