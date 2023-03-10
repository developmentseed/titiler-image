"""titiler-image dependencies."""

import json
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import httpx
from cachetools import TTLCache, cached
from fastapi import HTTPException, Query
from geojson_pydantic import MultiPolygon, Polygon
from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling

from titiler.core.dependencies import DefaultDependency

ResamplingName = Enum(  # type: ignore
    "ResamplingName", [(r.name, r.name) for r in Resampling]
)


@dataclass
class DatasetParams(DefaultDependency):
    """Dataset Optional parameters."""

    unscale: Optional[bool] = Query(
        False,
        title="Apply internal Scale/Offset",
        description="Apply internal Scale/Offset",
    )
    resampling_method: ResamplingName = Query(
        ResamplingName.nearest,  # type: ignore
        alias="resampling",
        description="Resampling method.",
    )

    def __post_init__(self):
        """Post Init."""
        self.resampling_method = self.resampling_method.value  # type: ignore


@cached(TTLCache(maxsize=512, ttl=3600))
def get_gcps(gcps_file: str) -> List[GroundControlPoint]:
    """Fetch and parse GCPS file."""
    if gcps_file.startswith("http"):
        body = httpx.get(gcps_file).json()

    else:
        with open(gcps_file, "r") as f:
            body = json.load(f)

    return [
        # GroundControlPoint(row, col, x, y, z)
        # https://github.com/allmaps/iiif-api/blob/georef/source/extension/georef/index.md#35-the-resourcecoords-property
        GroundControlPoint(
            f["properties"]["resourceCoords"][1],
            f["properties"]["resourceCoords"][0],
            *f["geometry"]["coordinates"],  # x, y, z
            id=f.get("id"),
        )
        for f in body["features"]
    ]


@cached(TTLCache(maxsize=512, ttl=3600))
def get_cutline(cutline_file: str) -> str:
    """Fetch and parse Cutline file."""
    if cutline_file.startswith("http"):
        body = httpx.get(cutline_file).json()

    else:
        with open(cutline_file, "r") as f:
            body = json.load(f)

    # We assume the geojson is a Feature (not a Feature Collectionw)
    if "geometry" in body:
        body = body["geometry"]

    geom_type = body["type"]
    if geom_type == "Polygon":
        return Polygon.parse_obj(body).wkt

    elif geom_type == "MultiPolygon":
        return MultiPolygon.parse_obj(body).wkt

    else:
        raise HTTPException(
            status_code=400, detail=f"Invalid GeoJSON type: {geom_type}."
        )


@dataclass
class GCPSParams(DefaultDependency):
    """GCPS parameters."""

    gcps: Optional[List[GroundControlPoint]] = None
    cutline: Optional[str] = None

    def __init__(
        self,
        gcps: Optional[List[str]] = Query(
            None,
            title="Ground Control Points",
            description="Ground Control Points in form of `row (y), col (x), lon, lat, alt`",
        ),
        gcps_file: Optional[str] = Query(
            None,
            title="Ground Control Points GeoJSON path",
        ),
        cutline: Optional[str] = Query(
            None,
            title="WKT Image Cutline (equivalent of the SVG Selector)",
            description="WKT Polygon or MultiPolygon.",
        ),
        cutline_file: Optional[str] = Query(
            None,
            title="GeoJSON file for cutline",
        ),
    ):
        """Initialize GCPSParams and Cutline

        Note: We only want `gcps` or `cutline` to be forwarded to the reader so we use a custom `__init__` method used by FastAPI to parse the QueryParams.
        """
        if gcps:
            self.gcps: List[GroundControlPoint] = [  # type: ignore
                # WARNING: gpcs should be in form of `row (y), col (x), lon, lat, alt`
                GroundControlPoint(*list(map(float, gcps.split(","))))
                for gcps in gcps
            ]
        elif gcps_file:
            self.gcps = get_gcps(gcps_file)

        if self.gcps and len(self.gcps) < 3:
            raise HTTPException(
                status_code=400, detail="Need at least 3 gcps to wrap an image."
            )

        if cutline:
            self.cutline = cutline

        elif cutline_file:
            self.cutline = get_cutline(cutline_file)
