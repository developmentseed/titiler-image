"""titiler-image dependencies."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from fastapi import Query
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
