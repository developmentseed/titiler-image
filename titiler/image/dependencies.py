"""titiler-image dependencies."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling

from titiler.core.dependencies import DefaultDependency

from fastapi import HTTPException, Query

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


@dataclass
class GCPSParams(DefaultDependency):
    """GCPS parameters."""

    gcps: Optional[List[str]] = Query(
        None,
        title="Ground Control Points",
        description="Ground Control Points",
    )

    def __post_init__(self):
        """Post Init."""
        if self.gcps:
            self.gcps: List[GroundControlPoint] = [  # type: ignore
                GroundControlPoint(*list(map(float, gcps.split(","))))
                for gcps in self.gcps
            ]
            if len(self.gcps) < 3:
                raise HTTPException(
                    status_code=400, detail="Need at least 3 gcps to wrap an image."
                )
