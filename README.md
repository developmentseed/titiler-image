# **Work In Progress**

This project is not yet at a `release` stage and should be considered as `Work In Progress`. Any contribution is welcome.

<p align="center">
  <p align="center">TiTiler Image.</p>
</p>

<p align="center">
  <a href="https://github.com//developmentseed/titiler-image/actions?query=workflow%3ACI" target="_blank">
      <img src="https://github.com/developmentseed/titiler-image/workflows/CI/badge.svg" alt="Test">
  </a>
  <a href="https://codecov.io/gh//developmentseed/titiler-image" target="_blank">
      <img src="https://codecov.io/gh//developmentseed/titiler-image/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/titiler.image" target="_blank">
      <img src="https://img.shields.io/pypi/v/titiler.image?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://github.com//developmentseed/titiler-image/blob/main/LICENSE" target="_blank">
      <img src="https://img.shields.io/github/license//developmentseed/titiler-image.svg" alt="License">
  </a>
</p>

---

**Documentation**:

**Source Code**: <a href="https://github.com/developmentseed/titiler-image" target="_blank">https://github.com/developmentseed/titiler-image</a>

---

`TiTiler.image` is a [titiler](https://github.com/developmentseed/titiler) extension to work with non-geo images.

## Installation

To install from PyPI and run:

```bash
# Make sure to have pip up to date
$ python -m pip install -U pip

$ python -m pip install titiler.image
```

To install from sources and run for development:

```
$ git clone https://github.com/developmentseed/titiler-image.git
$ cd titiler-image
$ python -m pip install -e .
```

## Launch

```
$ pip install uvicorn
$ uvicorn titiler.image.main:app --reload
```

### Using Docker

```
$ git clone https://github.com/developmentseed/titiler-image.git
$ cd titiler-pgstac
$ docker-compose up --build tiler
```

It runs `titiler.image` using Gunicorn web server. To run Uvicorn based version:

```
$ docker-compose up --build tiler-uvicorn
```

## Factories

`titiler-image` provide multiple endpoint Factories (see https://developmentseed.org/titiler/advanced/tiler_factories/)

### MetadataFactory

#### Endpoints

- `/info?url={...}`
- `/metadata?url={...}`

```python
from fastapi import FastAPI
from titiler.image.factory import MetadataFactory

app = FastAPI()
meta = MetadataFactory()
app.include_router(meta.router)
```

### IIIFFactory

#### Endpoints

- `/{identifier}/info.json`: IIIF Image Information Request
- `/{identifier}`: Redirect do the Image Information Request endpoint
- `/{identifier}/{region}/{size}/{rotation}/{quality}.{format}`: IIIF Image Request
- `/{identifier}/viewer`: Simple IIIF viewer (not part of the IIIF specification)

```python
from fastapi import FastAPI
from titiler.image.factory import IIIFFactory

app = FastAPI()
iiif = IIIFFactory()
app.include_router(iiif.router)
```

### LocalTilerFactory

#### Endpoints

- `/tilejson.json?url={...}`: TileJSON document
- `/tiles/{z}/{x}/{y}[@{scale}x.{format}]?url={...}`: Tiles endpoint
- `/viewer?url={...}`: Simple local tiles viewer

```python
from fastapi import FastAPI
from titiler.image.factory import LocalTilerFactory

app = FastAPI()
local_tiles = LocalTilerFactory()
app.include_router(local_tiles.router)
```

### GeoTilerFactory

This is a lightweight version of `titiler.core.factory.TilerFactory`.

#### Endpoints

- `/info[.geojson]?url={...}`: Dataset info (with geographic information)
- `[/TileMatrixSetId]/tilejson.json?url={...}`: TileJSON document
- `/tiles[/TileMatrixSetId]/{z}/{x}/{y}[@{scale}x.{format}]?url={...}`: Tiles endpoint
- `[/{TileMatrixSetId}]/WMTSCapabilities.xml`: OGC WMTS document
- `[/{TileMatrixSetId}]/map?url={...}`: Simple dataset viewer
- `/preview[.{format}]?url={...}`: Preview image from a dataset

```python
from fastapi import FastAPI
from titiler.image.factory import GeoTilerFactory

app = FastAPI()
geo = GeoTilerFactory()
app.include_router(geo.router)
```

### DeepZoomFactory

#### Endpoints

- `/deepzoom.dzi?url={...}`: DeepZoom metadata.
- `/{z}/{x}_{y}[.{format}]?url={...}`: DeepZoom Tiles
- `/deepzoom.html?url={...}`: Deepzoom viewer

```python
from fastapi import FastAPI
from titiler.image.factory import DeepZoomFactory

app = FastAPI()
deepzoom = DeepZoomFactory()
app.include_router(deepzoom.router)
```

All together

```python
app = FastAPI()

meta = MetadataFactory()
app.include_router(meta.router, tags=["Metadata"])

iiif = IIIFFactory(router_prefix="/iiif")
app.include_router(iiif.router, tags=["IIIF"], prefix="/iiif")

image_tiles = LocalTilerFactory(router_prefix="/image")
app.include_router(image_tiles.router, tags=["Local Tiles"], prefix="/image")

geo_tiles = GeoTilerFactory(
    reader=GCPSReader, reader_dependency=GCPSParams, router_prefix="/geo"
)
app.include_router(geo_tiles.router, tags=["Geo Tiles"], prefix="/geo")

deepzoom = DeepZoomFactory(router_prefix="/deepzoom")
app.include_router(deepzoom.router, tags=["Deepzoom"], prefix="/deepzoom")
```

![](https://user-images.githubusercontent.com/10407788/222417904-98b2dc2b-3e4d-43cf-a883-9dc2355f81f4.png)


## Contribution & Development

See [CONTRIBUTING.md](https://github.com//developmentseed/titiler-image/blob/main/CONTRIBUTING.md)

## License

See [LICENSE](https://github.com//developmentseed/titiler-image/blob/main/LICENSE)

## Authors

See [contributors](https://github.com/developmentseed/titiler-image/graphs/contributors) for a listing of individual contributors.

## Changes

See [CHANGES.md](https://github.com/developmentseed/titiler-image/blob/main/CHANGES.md).
