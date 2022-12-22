"""TiTiler-Image FastAPI application."""

import math
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import numpy
from affine import Affine
from rasterio import windows
from rasterio.warp import reproject
from rio_tiler.io import ImageReader
from rio_tiler.models import ImageData, Info
from rio_tiler.types import ColorMapType

from titiler.core.dependencies import (
    BidxExprParams,
    ColorMapParams,
    HistogramParams,
    ImageParams,
    RescalingParams,
    StatisticsParams,
)
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.middleware import CacheControlMiddleware
from titiler.core.models.mapbox import TileJSON
from titiler.core.models.responses import Statistics
from titiler.core.resources.enums import ImageType, MediaType
from titiler.core.resources.responses import JSONResponse, XMLResponse
from titiler.image import __version__ as titiler_image_version
from titiler.image.dependencies import DatasetParams
from titiler.image.models import iiifInfo
from titiler.image.resources.enums import IIIFImageFormat, IIIFQuality
from titiler.image.settings import api_settings, iiif_settings

from fastapi import Depends, FastAPI, HTTPException, Path, Query

from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.templating import Jinja2Templates
from starlette_cramjam.middleware import CompressionMiddleware

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore

# TODO: mypy fails in python 3.9, we need to find a proper way to do this
templates = Jinja2Templates(directory=str(resources_files(__package__) / "templates"))  # type: ignore

app = FastAPI(title=api_settings.name, version=titiler_image_version)

add_exception_handlers(app, DEFAULT_STATUS_CODES)

# Set all CORS enabled origins
if api_settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

app.add_middleware(
    CompressionMiddleware,
    minimum_size=0,
    exclude_mediatype={
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/jp2",
        "image/webp",
    },
)

app.add_middleware(
    CacheControlMiddleware,
    cachecontrol=api_settings.cachecontrol,
    exclude_path={r"/healthz"},
)

###############################################################################
# Deepzoom Endpoints
img_endpoint_params: Dict[str, Any] = {
    "responses": {
        200: {
            "content": {
                "image/png": {},
                "image/jpeg": {},
                "image/jpg": {},
                "image/webp": {},
                "image/jp2": {},
                "image/tiff; application=geotiff": {},
                "application/x-binary": {},
            },
            "description": "Return an image.",
        }
    },
    "response_class": Response,
}


@app.get(
    "/info",
    response_model=Info,
    response_model_exclude_none=True,
    response_class=JSONResponse,
    responses={200: {"description": "Return dataset's basic info."}},
    tags=["metadata"],
)
def info(src_path: str = Query(description="Dataset URL", alias="url")):
    """Return Image metadata."""
    with ImageReader(src_path) as dst:
        return dst.info()


# GET endpoint
@app.get(
    "/statistics",
    response_class=JSONResponse,
    response_model=Statistics,
    responses={
        200: {
            "content": {"application/json": {}},
            "description": "Return dataset's statistics.",
        }
    },
    tags=["metadata"],
)
def statistics(
    src_path: str = Query(description="Dataset URL", alias="url"),
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
# DEEPZOOM
###############################################################################
@app.get("/deepzoom.dzi", response_class=XMLResponse, tags=["deepzoom"])
def deepzoom(
    request: Request,
    src_path: str = Query(description="Dataset URL", alias="url"),
    format: ImageType = Query(
        ImageType.png, description="Output image type. Defaults to PNG."
    ),
):
    """DeepZoom metadata."""
    with ImageReader(src_path) as dst:
        info = dst.info()

    return templates.TemplateResponse(
        name="deepzoom.xml",
        context={"request": request, "info": info, "format": format},
        media_type=MediaType.xml.value,
    )


# @app.get("/deepzoom/{z}/{x}_{y}", **img_endpoint_params, tags=["deepzoom"])
# @app.get("/deepzoom/{z}/{x}_{y}.{format}", **img_endpoint_params, tags=["deepzoom"])
# def deepzoom_tile(
#     level: int = Path(..., alias="z"),
#     column: int = Path(..., alias="x"),
#     row: int = Path(..., alias="y"),
#     format: ImageType = Query(ImageType.png, description="Output image type. Defaults to PNG."),
#     src_path: str = Query(description="Dataset URL", alias="url"),
#     layer_params: BidxExprParams = Depends(),
#     dataset_params: DatasetParams = Depends(),
#     rescale: Optional[List[Tuple[float, ...]]] = Depends(RescalingParams),
#     color_formula: Optional[str] = Query(
#         None,
#         title="Color Formula",
#         description="rio-color formula (info: https://github.com/mapbox/rio-color)",
#     ),
#     colormap: Optional[ColorMapType] = Depends(ColorMapParams),
#     add_mask: Optional[bool] = Query(
#         None, alias="return_mask", description="Add mask to the output data."
#     )
# ):
#     """DeepZoom tile."""
#     tile_size = 254
#     tile_overlap = 1

#     with ImageReader(src_path) as dst:
#         max_dimension = max(dst.dataset.width, dst.dataset.height)
#         max_level = int(math.ceil(math.log(max_dimension, 2))) + 1
#         assert 0 <= level and level < max_level, 'Invalid pyramid level'

#         print(max_dimension)
#         print(max_level)

#         # Overview Size
#         # level_width = dst.dataset.width // 2 ** (max_level - level)
#         # level_height = dst.dataset.height // 2 ** (max_level - level)
#         scale = math.pow(0.5, max_level - 1 - level)
#         level_width = int(math.ceil(dst.dataset.width * scale))
#         level_height = int(math.ceil( dst.dataset.height * scale))

#         print(level_height, level_width)

#         # Nb tiles for Ovr
#         level_x_tile = int(math.ceil(level_width / tile_size))
#         level_y_tile = int(math.ceil(level_height / tile_size))

#         print(level_x_tile, level_y_tile)

#         offset_x = 0 if column == 0 else tile_overlap
#         offset_y = 0 if row == 0 else tile_overlap

#         x = (column * tile_size) - offset_x
#         y = (row * tile_size) - offset_y
#         w = tile_size + (1 if column == 0 else 2) * tile_overlap
#         h = tile_size + (1 if row == 0 else 2) * tile_overlap

#         w = min(w, level_width - x)
#         h = min(h, level_height - y)

#         print((x, y, x + w, y + h))

#         # Output Size
#         width = min(tile_size, level_width - (tile_size * (level_x_tile - 1))) if column == level_x_tile - 1 else tile_size
#         height = min(tile_size, level_height - (tile_size * (level_y_tile - 1))) if row == level_y_tile - 1 else tile_size

#         print(width, height)

#         # BBox
#         x_origin = (dst.dataset.width / level_width) * tile_size * column
#         y_origin = (dst.dataset.height / level_height) * tile_size * row
#         x_max = min(dst.dataset.width, x_origin + dst.dataset.width / level_width * width)
#         y_max = min(dst.dataset.height, y_origin + dst.dataset.height / level_height * height)

#         print(x_origin, y_origin, x_max, y_max)

#         w = windows.from_bounds(
#             x_origin,
#             y_max,
#             x_max,
#             y_origin,
#             transform=dst.transform,
#         )
#         image = dst.read(
#             window=w,
#             width=width,
#             height=height,
#             **layer_params,
#             **dataset_params,
#         )
#         dst_colormap = getattr(dst, "colormap", None)

#         if rescale:
#             image.rescale(rescale)

#         if color_formula:
#             image.apply_color_formula(color_formula)

#         content = image.render(
#             add_mask=add_mask if add_mask is not None else True,
#             img_format=format.driver,
#             colormap=colormap or dst_colormap,
#             **format.profile,
#         )

#     return Response(content, media_type=format.mediatype)


# @app.get("/deepzoom.html", response_class=HTMLResponse, tags=["deepzoom"])
# def deepzoom_viewer(
#     request: Request,
#     src_path: str = Query(description="Dataset URL", alias="url"),
#     format: ImageType = Query(ImageType.png, description="Output image type. Defaults to PNG."),
#     layer_params: BidxExprParams = Depends(),  # noqa
#     dataset_params: DatasetParams = Depends(),  # noqa
#     rescale: Optional[List[Tuple[float, ...]]] = Depends(RescalingParams),  # noqa
#     color_formula: Optional[str] = Query(  # noqa
#         None,
#         title="Color Formula",
#         description="rio-color formula (info: https://github.com/mapbox/rio-color)",
#     ),
#     colormap: Optional[ColorMapType] = Depends(ColorMapParams),  # noqa
#     add_mask: Optional[bool] = Query(  # noqa
#         None, alias="return_mask", description="Add mask to the output data."
#     )
# ):
#     """DeepZoom metadata."""
#     route_params: Dict[str, Any] = {
#         "z": "{z}",
#         "x": "{x}",
#         "y": "{y}",
#         "format": format.value,
#     }
#     dpz_url = app.router.url_path_for("deepzoom_tile", **route_params)

#     qs_key_to_remove = ["format"]
#     qs = [
#         (key, value)
#         for (key, value) in request.query_params._list
#         if key.lower() not in qs_key_to_remove
#     ]
#     if qs:
#         dpz_url += f"?{urllib.parse.urlencode(qs)}"

#     with ImageReader(src_path) as dst:
#         info = dst.info()

#     return templates.TemplateResponse(
#         name="deepzoom.html",
#         context={
#             "request": request,
#             "endpoint": dpz_url,
#             "width": info.width,
#             "height": info.height
#         },
#         media_type=MediaType.html.value,
#     )


###############################################################################
# Tiles
###############################################################################
@app.get(
    "/tilejson.json",
    response_model=TileJSON,
    responses={200: {"description": "Return a tilejson"}},
    response_model_exclude_none=True,
    tags=["tiles"],
)
def tilejson(
    request: Request,
    src_path: str = Query(description="Dataset URL", alias="url"),
    tile_format: Optional[ImageType] = Query(
        None, description="Output image type. Default is auto."
    ),
    tile_scale: Optional[int] = Query(
        None, gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."
    ),
    minzoom: Optional[int] = Query(None, description="Overwrite default minzoom."),
    maxzoom: Optional[int] = Query(None, description="Overwrite default maxzoom."),
    layer_params: BidxExprParams = Depends(),  # noqa
    dataset_params: DatasetParams = Depends(),  # noqa
    rescale: Optional[List[Tuple[float, ...]]] = Depends(RescalingParams),  # noqa
    color_formula: Optional[str] = Query(
        None,  # noqa
        title="Color Formula",
        description="rio-color formula (info: https://github.com/mapbox/rio-color)",
    ),
    colormap: Optional[ColorMapType] = Depends(ColorMapParams),  # noqa
    add_mask: Optional[bool] = Query(  # noqa
        None, alias="return_mask", description="Add mask to the output data."
    ),
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

    tiles_url = app.router.url_path_for("tile", **route_params)

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


@app.get("/tiles/{z}/{x}/{y}", **img_endpoint_params, tags=["tiles"])
@app.get("/tiles/{z}/{x}/{y}.{format}", **img_endpoint_params, tags=["tiles"])
@app.get("/tiles/{z}/{x}/{y}@{scale}x", **img_endpoint_params, tags=["tiles"])
@app.get("/tiles/{z}/{x}/{y}@{scale}x.{format}", **img_endpoint_params, tags=["tiles"])
def tile(
    z: int,
    x: int,
    y: int,
    scale: Optional[int] = Query(
        None, gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."
    ),
    format: ImageType = Query(
        ImageType.png, description="Output image type. Defaults to PNG."
    ),
    src_path: str = Query(description="Dataset URL", alias="url"),
    layer_params: BidxExprParams = Depends(),
    dataset_params: DatasetParams = Depends(),
    rescale: Optional[List[Tuple[float, ...]]] = Depends(RescalingParams),
    color_formula: Optional[str] = Query(
        None,
        title="Color Formula",
        description="rio-color formula (info: https://github.com/mapbox/rio-color)",
    ),
    colormap: Optional[ColorMapType] = Depends(ColorMapParams),
    add_mask: Optional[bool] = Query(
        None, alias="return_mask", description="Add mask to the output data."
    ),
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

    if not format:
        format = ImageType.jpeg if image.mask.all() else ImageType.png

    content = image.render(
        add_mask=add_mask if add_mask is not None else True,
        img_format=format.driver,
        colormap=colormap or dst_colormap,
        **format.profile,
    )

    return Response(content, media_type=format.mediatype)


@app.get("/viewer", response_class=HTMLResponse, tags=["tiles"])
def image_viewer(
    request: Request,
    src_path: str = Query(description="Dataset URL", alias="url"),  # noqa
    tile_format: Optional[ImageType] = Query(  # noqa
        None, description="Output image type. Default is auto."
    ),
    tile_scale: Optional[int] = Query(  # noqa
        None, gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."
    ),
    minzoom: Optional[int] = Query(  # noqa
        None, description="Overwrite default minzoom."
    ),
    maxzoom: Optional[int] = Query(  # noqa
        None, description="Overwrite default maxzoom."
    ),
    layer_params: BidxExprParams = Depends(),  # noqa
    dataset_params: DatasetParams = Depends(),  # noqa
    rescale: Optional[List[Tuple[float, ...]]] = Depends(RescalingParams),  # noqa
    color_formula: Optional[str] = Query(
        None,  # noqa
        title="Color Formula",
        description="rio-color formula (info: https://github.com/mapbox/rio-color)",
    ),
    colormap: Optional[ColorMapType] = Depends(ColorMapParams),  # noqa
    add_mask: Optional[bool] = Query(  # noqa
        None, alias="return_mask", description="Add mask to the output data."
    ),
):
    """Return Simple Image viewer."""
    tilejson_url = app.router.url_path_for("tilejson")
    if request.query_params._list:
        tilejson_url += f"?{urllib.parse.urlencode(request.query_params._list)}"

    return templates.TemplateResponse(
        name="local-image.html",
        context={
            "request": request,
            "tilejson_endpoint": tilejson_url,
        },
        media_type=MediaType.html.value,
    )


###############################################################################
# IIIF
###############################################################################

# application/ld+json or application/json
@app.get(
    "/{identifier}/info.json",
    response_model=iiifInfo,
    responses={200: {"description": "Image Information Request"}},
    response_model_exclude_none=True,
    tags=["iiif"],
)
def iiif_info(
    identifier: str = Path(description="Dataset URL"),
):
    """Image Information Request."""
    identifier = urllib.parse.unquote(identifier)
    with ImageReader(identifier) as dst:
        # If overviews
        # Set Sizes
        # Set Tiles (using min/max zooms)
        return {
            "id": identifier,
            "width": dst.dataset.width,
            "height": dst.dataset.height,
        }


def _percent(x: float, y: float) -> float:
    return (x / 100) * y


def _get_sizes(
    w: int,
    h: int,
    max_width: int = None,
    max_height: int = None,
    max_area: int = None,
) -> Tuple[int, int]:
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


def rotate(img: ImageData, angle: float, expand: bool = False):
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
        img.data,
        data,
        src_crs="epsg:4326",  # Fake CRS
        src_transform=Affine.identity(),
        dst_crs="epsg:4326",  # Fake CRS
        dst_transform=rotated_affine,
    )

    # Rotate the mask
    mask = numpy.zeros((nh, nw), dtype=img.mask.dtype)
    _ = reproject(
        img.mask,
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


@app.get(
    "/{identifier}/{region}/{size}/{rotation}/{quality}.{format}",
    **img_endpoint_params,
    tags=["iiif"],
)
def iiif_image(  # noqa
    identifier: str = Query(description="Dataset URL"),
    region: str = Path(
        description="The region parameter defines the rectangular portion of the underlying image content to be returned."
    ),
    size: str = Path(
        description="The size parameter specifies the dimensions to which the extracted region, which might be the full image, is to be scaled."
    ),
    rotation: str = Path(
        description="The rotation parameter specifies mirroring and rotation"
    ),
    quality: IIIFQuality = Query(
        IIIFQuality.default,
        description="The quality parameter determines whether the image is delivered in color, grayscale or black and white.",
    ),
    format: IIIFImageFormat = Path(
        description="The format of the returned image is expressed as a suffix, mirroring common filename extensions, at the end of the URI."
    ),
    # TiTiler Extension
    layer_params: BidxExprParams = Depends(),
    dataset_params: DatasetParams = Depends(),
    rescale: Optional[List[Tuple[float, ...]]] = Depends(RescalingParams),
    color_formula: Optional[str] = Query(
        None,
        title="Color Formula",
        description="rio-color formula (info: https://github.com/mapbox/rio-color)",
    ),
    colormap: Optional[ColorMapType] = Depends(ColorMapParams),
    add_mask: Optional[bool] = Query(
        None, alias="return_mask", description="Add mask to the output data."
    ),
):
    """IIIF Image Request.

    ref: https://iiif.io/api/image/3.0

    """
    identifier = urllib.parse.unquote(identifier)

    with ImageReader(identifier) as dst:
        dst_width = dst.dataset.width
        dst_height = dst.dataset.height

        #################################################################################
        # Region
        # full, square, x,y,w,h, pct:x,y,w,h
        #################################################################################
        window = windows.Window(
            col_off=0, row_off=0, width=dst_width, height=dst_height
        )
        if region == "full":
            pass

        elif region == "square":
            max_size = max(dst_width, dst_height)
            # TODO: center bbox
            window = windows.from_bounds(
                0, max_size, max_size, 0, transform=dst.dataset.transform
            )

        elif region.startswith("pct:"):
            x, y, w, h = list(map(float, region.replace("pct:", "").split(",")))
            if max(x, y, w, h) > 100 or min(x, y, w, h) < 0:
                raise HTTPException(
                    status_code=400, detail=f"Invalid Region parameter: {region}."
                )

            x = round(_percent(dst_width, x))
            y = round(_percent(dst_height, y))
            w = round(_percent(dst_width, w))
            h = round(_percent(dst_height, h))

            w = min(dst_width - x, w + x)
            h = min(dst_height - y, h + y)

            window = windows.Window(col_off=x, row_off=y, width=w, height=h)

        elif len(region.split(",")) == 4:
            x, y, w, h = list(map(float, region.split(",")))

            # Service should return an image cropped at the image’s edge, rather than adding empty space.
            # w = min(dst_width - x, w + x)
            # h = min(dst_height - y, h + y)

            window = windows.Window(col_off=x, row_off=y, width=w, height=h)

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
        # Size
        # Formats are: w, ,h w,h pct:p !w,h full max ^w, ^,h ^w,h
        #################################################################################
        out_width, out_height = window.width, window.height
        aspect_ratio = out_width / out_height

        if size == "max":
            # max: The extracted region is returned at the maximum size available, but will not be upscaled.
            # The resulting image will have the pixel dimensions of the extracted region,
            # unless it is constrained to a smaller size by maxWidth, maxHeight, or maxArea
            out_width, out_height = _get_sizes(
                out_width,
                out_height,
                max_width=iiif_settings.max_width,
                max_height=iiif_settings.max_height,
                max_area=iiif_settings.max_area,
            )

        elif size == "^max":
            # ^max: The extracted region is scaled to the maximum size permitted by maxWidth, maxHeight, or maxArea.
            # If the resulting dimensions are greater than the pixel width and height of the extracted region, the extracted region is upscaled.
            if aspect_ratio > 1:
                out_width = max(out_width, iiif_settings.max_width)
                out_height = math.ceil(out_width / aspect_ratio)
            else:
                out_height = max(out_height, iiif_settings.max_height)
                out_width = math.ceil(aspect_ratio * out_height)

            out_width, out_height = _get_sizes(
                out_width,
                out_height,
                max_area=iiif_settings.max_area,
            )

        elif size.startswith("pct:"):
            # pct:n: The width and height of the returned image is scaled to n percent of the width and height of the extracted region.
            # The value of n must not be greater than 100.
            pct_size = float(size.replace("pct:", ""))
            if pct_size > 100 or pct_size < 0:
                raise HTTPException(
                    status_code=400, detail=f"Invalid Size parameter: {size}."
                )

            out_width = round(_percent(out_width, pct_size))
            out_height = round(_percent(out_height, pct_size))

        elif size.startswith("^pct:"):
            # ^pct:n: The width and height of the returned image is scaled to n percent of the width and height of the extracted region.
            # For values of n greater than 100, the extracted region is upscaled.
            pct_size = float(size.replace("^pct:", ""))
            if pct_size < 0:
                raise HTTPException(
                    status_code=400, detail=f"Invalid Size parameter: {size}."
                )

            out_width = round(_percent(out_width, pct_size))
            out_height = round(_percent(out_height, pct_size))

        elif size.split(","):
            sizes = size.split(",")
            if size.startswith("^!"):
                # TODO
                pass
                # ^!w,h	The extracted region is scaled so that the width and height of the returned image are not greater than w and h, while maintaining the aspect ratio. The returned image must be as large as possible but not larger than w, h, or server-imposed limits.

            elif size.startswith("!"):
                # !w,h	The extracted region is scaled so that the width and height of the returned image are not greater than w and h, while maintaining the aspect ratio. The returned image must be as large as possible but not larger than the extracted region, w or h, or server-imposed limits.
                # TODO
                pass

            elif size.startswith("^"):
                # ^w,: The extracted region should be scaled so that the width of the returned image is exactly equal to w. If w is greater than the pixel width of the extracted region, the extracted region is upscaled.
                # ^,h: The extracted region should be scaled so that the height of the returned image is exactly equal to h. If h is greater than the pixel height of the extracted region, the extracted region is upscaled.
                # ^w,h:	The width and height of the returned image are exactly w and h. The aspect ratio of the returned image may be significantly different than the extracted region, resulting in a distorted image. If w and/or h are greater than the corresponding pixel dimensions of the extracted region, the extracted region is upscaled.
                # TODO
                pass

            elif size.endswith(","):
                # w,: The extracted region should be scaled so that the width of the returned image is exactly equal to w.
                # The value of w must not be greater than the width of the extracted region.
                out_width = int(sizes[0])
                if out_width > window.width:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid 'w' parameter: {out_width} (greater than region width {window.width}).",
                    )
                out_height = math.ceil(out_width / aspect_ratio)

            elif size.startswith(","):
                # ,h: The extracted region should be scaled so that the height of the returned image is exactly equal to h.
                # The value of h must not be greater than the height of the extracted region.
                out_height = int(sizes[1])
                if out_height > window.height:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid 'h' parameter: {out_height} (greater than region height {window.height}).",
                    )
                out_width = math.ceil(aspect_ratio * out_height)

            elif len(sizes) == 2:
                # w,h: The width and height of the returned image are exactly w and h.
                # The aspect ratio of the returned image may be significantly different than the extracted region, resulting in a distorted image.
                # The values of w and h must not be greater than the corresponding pixel dimensions of the extracted region.
                out_width, out_height = list(map(int, sizes))

            else:
                raise HTTPException(
                    status_code=400, detail=f"Invalid Size parameter: {size}."
                )

        else:
            raise HTTPException(
                status_code=400, detail=f"Invalid Size parameter: {size}."
            )

        # Region THEN Size THEN Rotation THEN Quality THEN Format
        image = dst.read(
            window=window,
            width=int(out_width),
            height=int(out_height),
            **layer_params,
            **dataset_params,
        )
        dst_colormap = getattr(dst, "colormap", None)

        #################################################################################
        # Rotation
        # Formats are: n, !n
        #################################################################################
        if rotation.startswith("!"):
            rot = float(rotation.replace("!", ""))
            image = rotate(image, -rot, expand=True)
        else:
            rot = float(rotation)
            image = rotate(image, rot, expand=True)

    if rescale:
        image.rescale(rescale)

    if color_formula:
        image.apply_color_formula(color_formula)

    if quality == IIIFQuality.gray:
        colormap = dst_colormap = None
        image = image_to_grayscale(image)

    if quality == IIIFQuality.bitonal:
        colormap = dst_colormap = None
        image = image_to_bitonal(image)

    content = image.render(
        add_mask=add_mask if add_mask is not None else True,
        img_format=format.driver,
        colormap=colormap or dst_colormap,
        **format.profile,
    )
    return Response(content, media_type=format.mediatype)


###############################################################################
# Health Check Endpoint
@app.get(
    "/healthz",
    description="Health Check.",
    summary="Health Check.",
    operation_id="healthCheck",
    tags=["Health Check"],
)
def ping():
    """Health check."""
    return {"ping": "pong!"}
