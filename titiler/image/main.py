"""TiTiler-Image FastAPI application."""
import warnings

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from rasterio.errors import NotGeoreferencedWarning, RasterioIOError
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette_cramjam.middleware import CompressionMiddleware

from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.middleware import CacheControlMiddleware
from titiler.image import __version__ as titiler_image_version
from titiler.image.factory import (
    GeoTilerFactory,
    IIIFFactory,
    LocalTilerFactory,
    MetadataFactory,
)
from titiler.image.settings import api_settings

app = FastAPI(
    title=api_settings.name,
    openapi_url="/api",
    docs_url="/api.html",
    description="""titiler application to work with non-geo images.

---

**Source Code**: <a href="https://github.com/developmentseed/titiler-image" target="_blank">https://github.com/developmentseed/titiler-image</a>

---
    """,
    version=titiler_image_version,
    root_path=api_settings.root_path,
)

warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

DEFAULT_STATUS_CODES.update(
    {
        RasterioIOError: status.HTTP_404_NOT_FOUND,
        RequestValidationError: status.HTTP_400_BAD_REQUEST,
    }
)

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

meta = MetadataFactory()
app.include_router(meta.router, tags=["Metadata"])

iiif = IIIFFactory(router_prefix="/iiif")
app.include_router(iiif.router, tags=["IIIF"], prefix="/iiif")

image_tiles = LocalTilerFactory(router_prefix="/image")
app.include_router(image_tiles.router, tags=["Local Tiles"], prefix="/image")

geo_tiles = GeoTilerFactory(router_prefix="/geo")
app.include_router(geo_tiles.router, tags=["Geo Tiles"], prefix="/geo")

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
