"""test Local Tiler Factory endpoints."""

import os

from .conftest import parse_img

PREFIX = os.path.join(os.path.dirname(__file__), "fixtures")

boston_jpeg = os.path.join(PREFIX, "boston.jpg")
cog_gcps = os.path.join(PREFIX, "cog_gcps.tif")


def test_tilejson(app):
    """test tilejson endpoint."""
    response = app.get("/image/tilejson.json", params={"url": boston_jpeg})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    tiles = body.pop("tiles")
    expected = {
        "tilejson": "2.2.0",
        "version": "1.0.0",
        "scheme": "xyz",
        "minzoom": 0,
        "maxzoom": 5,
        "bounds": [0.0, 5352.0, 7696.0, 0.0],
        "center": [3848.0, 2676.0, 0],
    }
    assert body == expected
    assert tiles[0].startswith("http://testserver/image/tiles/{z}/{x}/{y}?")

    response = app.get("/image/tilejson.json", params={"url": cog_gcps})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    tiles = body.pop("tiles")
    expected = {
        "tilejson": "2.2.0",
        "version": "1.0.0",
        "scheme": "xyz",
        "minzoom": 0,
        "maxzoom": 2,
        "bounds": [0.0, 837.0, 1280.0, 0.0],
        "center": [640.0, 418.5, 0],
    }
    assert body == expected
    assert tiles[0].startswith("http://testserver/image/tiles/{z}/{x}/{y}?")

    response = app.get(
        "/image/tilejson.json",
        params={
            "url": cog_gcps,
            "minzoom": 2,
            "maxzoom": 4,
            "rescale": "0,700",
            "tile_format": "png",
            "tile_scale": 2,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    tiles = body.pop("tiles")
    expected = {
        "tilejson": "2.2.0",
        "version": "1.0.0",
        "scheme": "xyz",
        "minzoom": 2,
        "maxzoom": 4,
        "bounds": [0.0, 837.0, 1280.0, 0.0],
        "center": [640.0, 418.5, 2],
    }
    assert body == expected
    assert tiles[0].startswith("http://testserver/image/tiles/{z}/{x}/{y}@2x.png?")
    assert "rescale=0%2C700" in tiles[0]


def test_tiles(app):
    """test local tiles endpoint."""
    response = app.get("/image/tiles/0/0/0", params={"url": boston_jpeg})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    meta = parse_img(response.content)
    assert meta["width"] == 256
    assert meta["height"] == 256

    response = app.get(
        "/image/tiles/0/0/0@2x.jpg", params={"url": cog_gcps, "rescale": "0,700"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 512
    assert meta["height"] == 512
