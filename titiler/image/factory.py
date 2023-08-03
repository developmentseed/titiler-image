"""titiler.image factories."""

import abc
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Type

import jinja2
from fastapi import APIRouter, Depends, HTTPException, Path, Query, params
from fastapi.dependencies.utils import get_parameterless_sub_dependant
from pydantic import conint
from rasterio import windows
from rio_tiler.io import BaseReader, ImageReader
from rio_tiler.models import Info
from starlette.requests import Request
from starlette.responses import (
    HTMLResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from starlette.routing import Match, compile_path, replace_params
from starlette.templating import Jinja2Templates
from typing_extensions import Annotated

from titiler.core.dependencies import (
    BidxExprParams,
    ColorMapParams,
    DefaultDependency,
    HistogramParams,
    ImageParams,
    RescalingParams,
    StatisticsParams,
)
from titiler.core.factory import TilerFactory, img_endpoint_params
from titiler.core.models.mapbox import TileJSON
from titiler.core.models.responses import Statistics
from titiler.core.resources.enums import ImageType, MediaType
from titiler.core.resources.responses import JSONResponse
from titiler.core.routing import EndpointScope
from titiler.image.dependencies import DatasetParams, GCPSParams
from titiler.image.models import iiifInfo
from titiler.image.reader import Reader
from titiler.image.resources.enums import IIIFImageFormat
from titiler.image.settings import iiif_settings
from titiler.image.utils import (
    _get_sizes,
    _percent,
    accept_media_type,
    image_to_bitonal,
    image_to_grayscale,
    rotate,
)

DEFAULT_TEMPLATES = Jinja2Templates(
    directory="",
    loader=jinja2.ChoiceLoader([jinja2.PackageLoader(__package__, "templates")]),
)  # type:ignore


@dataclass  # type: ignore
class BaseFactory(metaclass=abc.ABCMeta):
    """BaseFactory.

    Abstract Base Class for endpoints factories.

    Note: This is a custom version of titiler.core.factory.BaseTilerFactory (striped of most options)

    """

    # FastAPI router
    router: APIRouter = field(default_factory=APIRouter)

    # Router Prefix is needed to find the path for /tile if the TilerFactory.router is mounted
    # with other router (multiple `.../tile` routes).
    # e.g if you mount the route with `/cog` prefix, set router_prefix to cog and
    router_prefix: str = ""

    # add dependencies to specific routes
    route_dependencies: List[Tuple[List[EndpointScope], List[params.Depends]]] = field(
        default_factory=list
    )

    templates: Jinja2Templates = DEFAULT_TEMPLATES

    def __post_init__(self):
        """Post Init: register route and configure specific options."""
        self.register_routes()

        for scopes, dependencies in self.route_dependencies:
            self.add_route_dependencies(scopes=scopes, dependencies=dependencies)

    @abc.abstractmethod
    def register_routes(self):
        """Register Routes."""
        ...

    def url_for(self, request: Request, name: str, **path_params: Any) -> str:
        """Return full url (with prefix) for a specific endpoint."""
        url_path = self.router.url_path_for(name, **path_params)
        base_url = str(request.base_url)
        if self.router_prefix:
            prefix = self.router_prefix.lstrip("/")
            # If we have prefix with custom path param we check and replace them with
            # the path params provided
            if "{" in prefix:
                _, path_format, param_convertors = compile_path(prefix)
                prefix, _ = replace_params(
                    path_format, param_convertors, request.path_params
                )
            base_url += prefix

        return str(url_path.make_absolute_url(base_url=base_url))

    def add_route_dependencies(
        self,
        *,
        scopes: List[EndpointScope],
        dependencies=List[params.Depends],
    ):
        """Add dependencies to routes.

        Allows a developer to add dependencies to a route after the route has been defined.

        """
        for route in self.router.routes:
            for scope in scopes:
                match, _ = route.matches({"type": "http", **scope})
                if match != Match.FULL:
                    continue

                # Mimicking how APIRoute handles dependencies:
                # https://github.com/tiangolo/fastapi/blob/1760da0efa55585c19835d81afa8ca386036c325/fastapi/routing.py#L408-L412
                for depends in dependencies[::-1]:
                    route.dependant.dependencies.insert(  # type: ignore
                        0,
                        get_parameterless_sub_dependant(
                            depends=depends, path=route.path_format  # type: ignore
                        ),
                    )

                # Register dependencies directly on route so that they aren't ignored if
                # the routes are later associated with an app (e.g. app.include_router(router))
                # https://github.com/tiangolo/fastapi/blob/58ab733f19846b4875c5b79bfb1f4d1cb7f4823f/fastapi/applications.py#L337-L360
                # https://github.com/tiangolo/fastapi/blob/58ab733f19846b4875c5b79bfb1f4d1cb7f4823f/fastapi/routing.py#L677-L678
                route.dependencies.extend(dependencies)  # type: ignore


###############################################################################
# Metadata Endpoints Factory
###############################################################################
@dataclass
class MetadataFactory(BaseFactory):
    """Metadata Factory."""

    def register_routes(self):
        """Register Routes."""

        @self.router.get(
            "/info",
            response_model=Info,
            response_model_exclude_none=True,
            response_class=JSONResponse,
            responses={200: {"description": "Return dataset's basic info."}},
        )
        def info(
            src_path: Annotated[
                str,
                Query(description="Dataset URL", alias="url"),
            ],
        ):
            """Return Image metadata."""
            with ImageReader(src_path) as dst:
                return dst.info()

        @self.router.get(
            "/statistics",
            response_class=JSONResponse,
            response_model=Statistics,
            responses={
                200: {
                    "content": {"application/json": {}},
                    "description": "Return dataset's statistics.",
                }
            },
        )
        def statistics(
            src_path: Annotated[
                str,
                Query(description="Dataset URL", alias="url"),
            ],
            layer_params: BidxExprParams = Depends(),
            dataset_params: DatasetParams = Depends(),
            image_params: ImageParams = Depends(),
            stats_params: StatisticsParams = Depends(),
            histogram_params: HistogramParams = Depends(),
        ):
            """Get Dataset statistics."""
            with ImageReader(src_path) as dst:
                return dst.statistics(
                    **layer_params,
                    **image_params,
                    **dataset_params,
                    **stats_params,
                    hist_options={**histogram_params},
                )


###############################################################################
# Local Tiles Endpoints Factory
###############################################################################
@dataclass
class LocalTilerFactory(BaseFactory):
    """Local Tiler Factory."""

    add_viewer: bool = True

    def register_routes(self):
        """Register Routes."""
        self.register_tiles()

        if self.add_viewer:
            self.register_viewer()

    def register_tiles(self):
        """Register Tile routes."""

        @self.router.get(
            "/tilejson.json",
            response_model=TileJSON,
            responses={200: {"description": "Return a TileJSON document"}},
            response_model_exclude_none=True,
        )
        def tilejson(
            request: Request,
            src_path: Annotated[
                str,
                Query(description="Dataset URL", alias="url"),
            ],
            tile_format: Annotated[
                Optional[ImageType],
                Query(description="Output image type. Default is auto."),
            ] = None,
            tile_scale: Annotated[
                Optional[int],
                Query(
                    gt=0,
                    lt=4,
                    description="Tile size scale. 1=256x256, 2=512x512...",
                ),
            ] = None,
            minzoom: Annotated[
                Optional[int],
                Query(description="Overwrite default minzoom."),
            ] = None,
            maxzoom: Annotated[
                Optional[int],
                Query(description="Overwrite default maxzoom."),
            ] = None,
            layer_params: BidxExprParams = Depends(),
            dataset_params: DatasetParams = Depends(),
            rescale: RescalingParams = Depends(),
            color_formula: Annotated[
                Optional[str],
                Query(
                    title="Color Formula",
                    description="rio-color formula (info: https://github.com/mapbox/rio-color)",
                ),
            ] = None,
            colormap: ColorMapParams = Depends(),
            add_mask: Annotated[
                Optional[bool],
                Query(
                    alias="return-mask",
                    description="Add mask to the output data.",
                ),
            ] = None,
        ):
            """return Tilejson doc."""
            route_params: Dict[str, Any] = {
                "z": "{z}",
                "x": "{x}",
                "y": "{y}",
            }

            if tile_scale:
                route_params["scale"] = tile_scale

            if tile_format:
                route_params["format"] = tile_format.value

            tiles_url = self.url_for(request, "tile", **route_params)

            qs_key_to_remove = [
                "tile_format",
                "tile_scale",
                "minzoom",
                "maxzoom",
            ]
            qs = [
                (key, value)
                for (key, value) in request.query_params._list
                if key.lower() not in qs_key_to_remove
            ]
            if qs:
                tiles_url += f"?{urllib.parse.urlencode(qs)}"

            with ImageReader(src_path) as dst:
                return {
                    "bounds": dst.geographic_bounds,
                    "minzoom": minzoom if minzoom is not None else dst.minzoom,
                    "maxzoom": maxzoom if maxzoom is not None else dst.maxzoom,
                    "tiles": [tiles_url],
                }

        @self.router.get("/tiles/{z}/{x}/{y}", **img_endpoint_params)
        @self.router.get("/tiles/{z}/{x}/{y}.{format}", **img_endpoint_params)
        @self.router.get("/tiles/{z}/{x}/{y}@{scale}x", **img_endpoint_params)
        @self.router.get("/tiles/{z}/{x}/{y}@{scale}x.{format}", **img_endpoint_params)
        def tile(
            z: Annotated[
                int,
                Path(description="Identifier (Z) selecting one of the scales."),
            ],
            x: Annotated[
                int,
                Path(description="Column (X) index of the tile."),
            ],
            y: Annotated[
                int,
                Path(description="Row (Y) index of the tile."),
            ],
            src_path: Annotated[str, Query(description="Dataset URL", alias="url")],
            scale: Annotated[
                Optional[conint(gt=0, le=4)], "Tile size scale. 1=256x256, 2=512x512..."
            ] = None,
            format: Annotated[
                ImageType,
                "Default will be automatically defined if the output image needs a mask (png) or not (jpeg).",
            ] = None,
            layer_params: BidxExprParams = Depends(),
            dataset_params: DatasetParams = Depends(),
            rescale: RescalingParams = Depends(),
            color_formula: Annotated[
                Optional[str],
                Query(
                    title="Color Formula",
                    description="rio-color formula (info: https://github.com/mapbox/rio-color)",
                ),
            ] = None,
            colormap: ColorMapParams = Depends(),
            add_mask: Annotated[
                Optional[bool],
                Query(
                    alias="return-mask",
                    description="Add mask to the output data.",
                ),
            ] = None,
        ):
            """Tile in Local TMS."""
            tilesize = scale * 256 if scale is not None else 256

            with ImageReader(src_path) as dst:
                image = dst.tile(
                    x,
                    y,
                    z,
                    tilesize=tilesize,
                    **layer_params,
                    **dataset_params,
                )
                dst_colormap = getattr(dst, "colormap", None)

            if rescale:
                image.rescale(rescale)

            if color_formula:
                image.apply_color_formula(color_formula)

            if cmap := colormap or dst_colormap:
                image = image.apply_colormap(cmap)

            if not format:
                format = ImageType.jpeg if image.mask.all() else ImageType.png

            content = image.render(
                add_mask=add_mask if add_mask is not None else True,
                img_format=format.driver,
                **format.profile,
            )

            return Response(content, media_type=format.mediatype)

    def register_viewer(self):
        """Register Viewer route."""

        @self.router.get("/viewer", response_class=HTMLResponse)
        def image_viewer(
            request: Request,
            src_path: Annotated[str, Query(description="Dataset URL", alias="url")],
            tile_format: Annotated[
                Optional[ImageType],
                Query(description="Output image type. Default is auto."),
            ] = None,
            tile_scale: Annotated[
                Optional[int],
                Query(
                    gt=0,
                    lt=4,
                    description="Tile size scale. 1=256x256, 2=512x512...",
                ),
            ] = None,
            minzoom: Annotated[
                Optional[int],
                Query(description="Overwrite default minzoom."),
            ] = None,
            maxzoom: Annotated[
                Optional[int],
                Query(description="Overwrite default maxzoom."),
            ] = None,
            layer_params: BidxExprParams = Depends(),
            dataset_params: DatasetParams = Depends(),
            rescale: RescalingParams = Depends(),
            color_formula: Annotated[
                Optional[str],
                Query(
                    title="Color Formula",
                    description="rio-color formula (info: https://github.com/mapbox/rio-color)",
                ),
            ] = None,
            colormap: ColorMapParams = Depends(),
            add_mask: Annotated[
                Optional[bool],
                Query(
                    alias="return-mask",
                    description="Add mask to the output data.",
                ),
            ] = None,
        ):
            """Return Simple Image viewer."""
            tilejson_url = self.url_for(request, "tilejson")
            if request.query_params._list:
                tilejson_url += f"?{urllib.parse.urlencode(request.query_params._list)}"

            return self.templates.TemplateResponse(
                name="local.html",
                context={
                    "request": request,
                    "tilejson_endpoint": tilejson_url,
                },
                media_type=MediaType.html.value,
            )


###############################################################################
# IIIF Endpoints Factory
###############################################################################
@dataclass
class IIIFFactory(BaseFactory):
    """IIIF Factory.

    Specification: https://iiif.io/api/image/3.0/
    """

    def register_routes(self):
        """Register Routes."""
        self.register_image_api()

    def register_image_api(self):  # noqa: C901
        """Register IIIF Image API routes."""

        @self.router.get(
            "/{identifier:path}/info.json",
            response_model=iiifInfo,
            response_model_exclude_none=True,
            responses={
                200: {
                    "description": "Image Information Request",
                    "content": {
                        "application/json": {},
                        "application/ld+json": {},
                    },
                },
            },
        )
        def iiif_info(
            request: Request,
            identifier: Annotated[
                str,
                Path(description="The identifier of the requested image."),
            ],
        ):
            """Image Information Request."""
            output_type = accept_media_type(
                request.headers.get("accept", ""),
                ["application/json", "application/ld+json"],
            )
            url_path = self.url_for(
                request,
                "iiif_baseuri",
                identifier=urllib.parse.quote_plus(identifier, safe=""),
            )

            identifier = urllib.parse.unquote(identifier)
            with ImageReader(identifier) as dst:
                # TODO: If overviews:
                # Set Sizes
                # Set Tiles (using min/max zooms)
                info = iiifInfo(
                    id=url_path,
                    width=dst.dataset.width,
                    height=dst.dataset.height,
                )

                if output_type == "application/ld+json":
                    return StreamingResponse(
                        iter((info.model_dump_json(exclude_none=True) + "\n",)),
                        media_type='application/ld+json;profile="http://iiif.io/api/image/3/context.json"',
                    )

            return info

        @self.router.get(
            "/{identifier:path}/{region}/{size}/{rotation}/{quality}.{format}",
            **img_endpoint_params,
        )
        def iiif_image(  # noqa: C901
            identifier: Annotated[
                str,
                Path(description="The identifier of the requested image."),
            ],
            region: Annotated[
                str,
                Path(
                    description="The region parameter defines the rectangular portion of the underlying image content to be returned."
                ),
            ],
            size: Annotated[
                str,
                Path(
                    description="The size parameter specifies the dimensions to which the extracted region, which might be the full image, is to be scaled."
                ),
            ],
            rotation: Annotated[
                str,
                Path(
                    description="The rotation parameter specifies mirroring and rotation",
                ),
            ],
            quality: Annotated[
                Literal["color", "gray", "bitonal", "default"],
                Path(
                    description="The quality parameter determines whether the image is delivered in color, grayscale or black and white.",
                ),
            ],
            format: Annotated[
                IIIFImageFormat,
                Path(
                    description="The format of the returned image is expressed as a suffix, mirroring common filename extensions, at the end of the URI."
                ),
            ],
            # TiTiler Extension
            layer_params: BidxExprParams = Depends(),
            dataset_params: DatasetParams = Depends(),
            rescale: RescalingParams = Depends(),
            color_formula: Annotated[
                Optional[str],
                Query(
                    title="Color Formula",
                    description="rio-color formula (info: https://github.com/mapbox/rio-color)",
                ),
            ] = None,
            colormap: ColorMapParams = Depends(),
            add_mask: Annotated[
                Optional[bool],
                Query(
                    alias="return-mask",
                    description="Add mask to the output data.",
                ),
            ] = None,
        ):
            """IIIF Image Request.

            ref: https://iiif.io/api/image/3.0

            """
            identifier = urllib.parse.unquote(identifier)
            with ImageReader(identifier) as dst:
                dst_width = dst.dataset.width
                dst_height = dst.dataset.height

                #################################################################################
                # REGION
                # full, square, x,y,w,h, pct:x,y,w,h
                #################################################################################
                window = windows.Window(
                    col_off=0, row_off=0, width=dst_width, height=dst_height
                )
                if region == "full":
                    # The full image is returned, without any cropping.
                    pass

                elif region == "square":
                    # The region is defined as an area where the width and height are both equal to the length of the shorter dimension of the full image.
                    # The region may be positioned anywhere in the longer dimension of the full image at the server’s discretion, and centered is often a reasonable default.
                    min_size = min(dst_width, dst_height)
                    x_off = (dst_width - min_size) // 2
                    y_off = (dst_height - min_size) // 2
                    window = windows.Window(
                        col_off=x_off, row_off=y_off, width=min_size, height=min_size
                    )

                elif region.startswith("pct:"):
                    # The region to be returned is specified as a sequence of percentages of the full image’s dimensions,
                    # as reported in the image information document.
                    # Thus, x represents the number of pixels from the 0 position on the horizontal axis, calculated as a percentage of the reported width.
                    # w represents the width of the region, also calculated as a percentage of the reported width.
                    # The same applies to y and h respectively.
                    x, y, w, h = list(map(float, region.replace("pct:", "").split(",")))
                    if max(x, y, w, h) > 100 or min(x, y, w, h) < 0:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid Region parameter: {region}.",
                        )

                    x = round(_percent(dst_width, x))
                    y = round(_percent(dst_height, y))
                    w = round(_percent(dst_width, w))
                    h = round(_percent(dst_height, h))

                    # Service should return an image cropped at the image’s edge, rather than adding empty space.
                    w = dst_width - x if w + x > dst_width else w
                    h = dst_height - y if h + y > dst_height else h

                    window = windows.Window(col_off=x, row_off=y, width=w, height=h)

                elif len(region.split(",")) == 4:
                    # The region of the full image to be returned is specified in terms of absolute pixel values.
                    # The value of x represents the number of pixels from the 0 position on the horizontal axis.
                    # The value of y represents the number of pixels from the 0 position on the vertical axis.
                    # Thus the x,y position 0,0 is the upper left-most pixel of the image. w represents
                    # the width of the region and h represents the height of the region in pixels.
                    x, y, w, h = list(map(float, region.split(",")))

                    # Service should return an image cropped at the image’s edge, rather than adding empty space.
                    w = dst_width - x if w + x > dst_width else w
                    h = dst_height - y if h + y > dst_height else h

                    try:
                        window = windows.Window(col_off=x, row_off=y, width=w, height=h)
                    except ValueError as e:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid Region parameter: {region}.",
                        ) from e

                else:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid Region parameter: {region}."
                    )

                if (
                    window.width <= 0
                    or window.height <= 0
                    or window.col_off > dst_width
                    or window.row_off > dst_height
                ):
                    raise HTTPException(
                        status_code=400, detail=f"Invalid Region parameter: {region}."
                    )

                #################################################################################
                # SIZE
                # Formats are: w, ,h w,h pct:p !w,h full max ^w, ^,h ^w,h
                #################################################################################
                out_width, out_height = window.width, window.height
                aspect_ratio = out_width / out_height

                if size == "max":
                    # max: The extracted region is returned at the maximum size available, but will not be upscaled.
                    # The resulting image will have the pixel dimensions of the extracted region,
                    # unless it is constrained to a smaller size by maxWidth, maxHeight, or maxArea
                    pass

                elif size == "^max":
                    # ^max: The extracted region is scaled to the maximum size permitted by maxWidth, maxHeight, or maxArea.
                    # If the resulting dimensions are greater than the pixel width and height of the extracted region, the extracted region is upscaled.
                    if aspect_ratio > 1:
                        out_width = (
                            max(out_width, iiif_settings.max_width)
                            if iiif_settings.max_width
                            else out_width
                        )
                        out_height = round(out_width / aspect_ratio)
                    else:
                        out_height = (
                            max(out_height, iiif_settings.max_height)
                            if iiif_settings.max_height
                            else out_height
                        )
                        out_width = round(aspect_ratio * out_height)

                elif size.startswith("pct:"):
                    # pct:n: The width and height of the returned image is scaled to n percent of the width and height of the extracted region.
                    # The value of n must not be greater than 100.
                    pct_size = float(size.replace("pct:", ""))
                    if pct_size > 100 or pct_size <= 0:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid Size parameter: {size} (must be between 0 and 100).",
                        )

                    out_width = round(_percent(out_width, pct_size))
                    out_height = round(_percent(out_height, pct_size))

                elif size.startswith("^pct:"):
                    # ^pct:n: The width and height of the returned image is scaled to n percent of the width and height of the extracted region.
                    # For values of n greater than 100, the extracted region is upscaled.
                    pct_size = float(size.replace("^pct:", ""))
                    if pct_size <= 0:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid Size parameter: {size} (must be greater than 0).",
                        )

                    out_width = round(_percent(out_width, pct_size))
                    out_height = round(_percent(out_height, pct_size))

                elif "," in size:
                    sizes = size.split(",")

                    if size.startswith("^!"):
                        # ^!w,h	The extracted region is scaled so that the width and height of the returned image are not greater than w and h, while maintaining the aspect ratio.
                        # The returned image must be as large as possible but not larger than w, h, or server-imposed limits.
                        max_width, max_height = list(
                            map(int, size.replace("^!", "").split(","))
                        )
                        if aspect_ratio > 1:
                            out_width = max_width
                            out_height = round(out_width / aspect_ratio)
                        else:
                            out_height = max_height
                            out_width = round(aspect_ratio * out_height)

                    elif size.startswith("!"):
                        # !w,h	The extracted region is scaled so that the width and height of the returned image are not greater than w and h, while maintaining the aspect ratio.
                        # The returned image must be as large as possible but not larger than the extracted region, w or h, or server-imposed limits.
                        max_width, max_height = list(
                            map(int, size.replace("!", "").split(","))
                        )

                        if aspect_ratio > 1:
                            out_width = max_width
                            out_height = round(out_width / aspect_ratio)
                        else:
                            out_height = max_height
                            out_width = round(aspect_ratio * out_height)

                        if out_width > window.width or out_height > window.height:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Invalid 'h,w' parameter: {size} (greater than region height {window.width},{window.height}).",
                            )

                    elif size.startswith("^"):
                        sizes = size.replace("^", "").split(",")

                        if size.endswith(","):
                            # ^w,: The extracted region should be scaled so that the width of the returned image is exactly equal to w.
                            # If w is greater than the pixel width of the extracted region, the extracted region is upscaled.
                            out_width = int(sizes[0])
                            out_height = round(out_width / aspect_ratio)

                        elif size.startswith("^,"):
                            # ^,h: The extracted region should be scaled so that the height of the returned image is exactly equal to h. If h is greater than the pixel height of the extracted region, the extracted region is upscaled.
                            out_height = int(sizes[1])
                            out_width = round(aspect_ratio * out_height)

                        elif sizes[0] and sizes[1]:
                            # ^w,h:	The width and height of the returned image are exactly w and h.
                            # The aspect ratio of the returned image may be significantly different than the extracted region, resulting in a distorted image.
                            # If w and/or h are greater than the corresponding pixel dimensions of the extracted region, the extracted region is upscaled.
                            out_width, out_height = list(map(int, sizes))

                    elif size.endswith(","):
                        # w,: The extracted region should be scaled so that the width of the returned image is exactly equal to w.
                        # The value of w must not be greater than the width of the extracted region.
                        out_width = int(sizes[0])
                        if out_width > window.width:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Invalid 'w' parameter: {out_width} (greater than region width {window.width}).",
                            )
                        out_height = round(out_width / aspect_ratio)

                    elif size.startswith(","):
                        # ,h: The extracted region should be scaled so that the height of the returned image is exactly equal to h.
                        # The value of h must not be greater than the height of the extracted region.
                        out_height = int(sizes[1])
                        if out_height > window.height:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Invalid 'h' parameter: {out_height} (greater than region height {window.height}).",
                            )
                        out_width = round(aspect_ratio * out_height)

                    elif sizes[0] and sizes[1]:
                        # w,h: The width and height of the returned image are exactly w and h.
                        # The aspect ratio of the returned image may be significantly different than the extracted region, resulting in a distorted image.
                        # The values of w and h must not be greater than the corresponding pixel dimensions of the extracted region.
                        out_width, out_height = list(map(int, sizes))
                        if out_width > window.width or out_height > window.height:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Invalid 'h,w' parameter: {size} (greater than region height {window.width},{window.height}).",
                            )

                    else:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid Size parameter: {size}."
                        )

                else:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid Size parameter: {size}."
                    )

                out_width, out_height = _get_sizes(
                    out_width,
                    out_height,
                    max_width=iiif_settings.max_width,
                    max_height=iiif_settings.max_height,
                    max_area=iiif_settings.max_area,
                )

                if out_width <= 1 or out_height <= 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid Size parameter: {size} resulting in size <=1 ({out_width},{out_height}).",
                    )

                image = dst.read(
                    window=window,
                    width=int(out_width),
                    height=int(out_height),
                    **layer_params,
                    **dataset_params,
                )
                dst_colormap = getattr(dst, "colormap", None)

            #################################################################################
            # ROTATION
            # Formats are: n, !n
            #################################################################################
            try:
                rot = float(rotation.replace("!", ""))
                if rot < 0 or rot > 360:
                    raise ValueError("Invalid rotation value")

            except (ValueError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid rotation parameter: {rotation}.",
                ) from e

            image = rotate(image, rot, expand=True, mirrored=rotation.startswith("!"))

            if rescale:
                image.rescale(rescale)

            if color_formula:
                image.apply_color_formula(color_formula)

            #################################################################################
            # QUALITY
            # one of default, color, gray or bitonal
            #################################################################################
            if quality == "gray":
                colormap = dst_colormap = None
                image = image_to_grayscale(image)

            elif quality == "bitonal":
                colormap = dst_colormap = None
                image = image_to_bitonal(image)

            if cmap := colormap or dst_colormap:
                image = image.apply_colormap(cmap)

            content = image.render(
                add_mask=add_mask if add_mask is not None else True,
                img_format=format.driver,
                **format.profile,
            )
            return Response(content, media_type=format.mediatype)

        @self.router.get(
            "/{identifier:path}",
            response_class=RedirectResponse,
            include_in_schema=False,
        )
        def iiif_baseuri(
            request: Request,
            identifier: Annotated[
                str, Path(description="The identifier of the requested image.")
            ],
        ):
            """Return Simple IIIF viewer.

            ref: https://iiif.io/api/image/3.0/#2-uri-syntax
            When the base URI is dereferenced, the interaction should result in the image information document.
            It is recommended that the response be a 303 status redirection to the image information document’s URI.
            Implementations may also exhibit other behavior for the base URI beyond the scope of this specification
            in response to HTTP request headers and methods.

            """
            url = self.url_for(request, "iiif_info", identifier=identifier)
            output_type = accept_media_type(
                request.headers.get("accept", ""),
                ["text/html"],
            )
            if output_type:
                return self.templates.TemplateResponse(
                    name="iiif.html",
                    context={
                        "request": request,
                        "info_endpoint": url,
                    },
                    media_type=MediaType.html.value,
                )

            return RedirectResponse(url)


###############################################################################
# Geo Tiler Factory
###############################################################################
@dataclass
class GeoTilerFactory(TilerFactory):
    """Like Tiler Factory but with less endpoints."""

    reader: Type[BaseReader] = Reader

    reader_dependency: Type[DefaultDependency] = GCPSParams

    # Rasterio Dataset Options (nodata, unscale, resampling)
    dataset_dependency: Type[DefaultDependency] = DatasetParams

    def register_routes(self):
        """This Method register routes to the router."""
        self.tile()
        self.tilejson()

        if self.add_viewer:
            self.map_viewer()
