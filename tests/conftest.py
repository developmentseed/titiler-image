"""``pytest`` configuration."""

import warnings
from typing import Any, Dict

import pytest
from rasterio.errors import NotGeoreferencedWarning
from rasterio.io import MemoryFile
from starlette.testclient import TestClient


def parse_img(content: bytes) -> Dict[Any, Any]:
    """Read tile image and return metadata."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=NotGeoreferencedWarning,
            module="rasterio",
        )
        with MemoryFile(content) as mem:
            with mem.open() as dst:
                return dst.profile


@pytest.fixture(autouse=True)
def app(monkeypatch):
    """Create app."""
    from titiler.image.main import app

    with TestClient(app) as app:
        yield app
