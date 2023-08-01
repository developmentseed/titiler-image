"""Test titiler.image IIIF endpoints."""

import os
import urllib

from .conftest import parse_img

PREFIX = os.path.join(os.path.dirname(__file__), "fixtures")

boston_jpeg = os.path.join(PREFIX, "boston_small.jpg")


def test_iiif_information_endpoints(app):
    """Test info endpoints."""
    identifier = urllib.parse.quote_plus(boston_jpeg, safe="")

    # # Make sure we got redirected
    # response = app.get(f"/iiif/{identifier}", follow_redirects=True)
    # assert response.history

    # assert response.status_code == 200
    # assert response.headers["content-type"] == "application/json"
    # bodyr = response.json()
    # assert bodyr["id"] == response.history[0].url

    response = app.get(f"/iiif/{identifier}/info.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert body["type"] == "ImageService3"
    assert body["width"] == 1000
    assert body["height"] == 695


def test_iiif_image_endpoint(app):
    """Test image endpoints."""
    identifier = urllib.parse.quote_plus(boston_jpeg, safe="")

    ###########################################################################
    # REGION
    # region=full
    response = app.get(f"/iiif/{identifier}/full/max/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1000
    assert meta["height"] == 695
    assert meta["count"] == 3
    assert meta["driver"] == "JPEG"

    # region=square
    response = app.get(f"/iiif/{identifier}/square/max/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == meta["height"]

    # region=x,y,w,h
    response = app.get(f"/iiif/{identifier}/0,0,10,20/max/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 10
    assert meta["height"] == 20

    # region=pct:x,y,w,h
    response = app.get(f"/iiif/{identifier}/pct:10,10,10,10/max/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 100
    assert meta["height"] == 70

    # region=Invalid
    response = app.get(f"/iiif/{identifier}/yo/max/0/default.jpg")
    assert response.status_code == 400

    # invalid region
    response = app.get(f"/iiif/{identifier}/0,1000,100,100/max/0/default.jpg")
    assert response.status_code == 400

    ###########################################################################
    # FORMAT
    # format=png
    response = app.get(f"/iiif/{identifier}/full/max/0/default.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    meta = parse_img(response.content)
    assert meta["count"] == 4
    assert meta["driver"] == "PNG"

    ###########################################################################
    # ROTATION
    # rotation=90
    response = app.get(f"/iiif/{identifier}/full/max/90/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 695
    assert meta["height"] == 1000

    # rotation=180
    response = app.get(f"/iiif/{identifier}/full/max/180/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1000
    assert meta["height"] == 695

    # rotation=-90
    response = app.get(f"/iiif/{identifier}/full/max/!90/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 695
    assert meta["height"] == 1000

    # rotation=invalid
    response = app.get(f"/iiif/{identifier}/full/max/!900/default.jpg")
    assert response.status_code == 400

    ###########################################################################
    # ROTATION

    ###########################################################################
    # SIZE
