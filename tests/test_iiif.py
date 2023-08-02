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
    # response = app.get(
    #     f"/iiif/{identifier}",
    #     follow_redirects=True,
    #     headers={"accept": "application/json"},
    # )
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

    response = app.get(
        f"/iiif/{identifier}/info.json",
        headers={"accept": "application/ld+json"},
    )
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == 'application/ld+json;profile="http://iiif.io/api/image/3/context.json"'
    )
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

    # region=extends beyond
    response = app.get(f"/iiif/{identifier}/0,0,1005,700/max/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1000
    assert meta["height"] == 695
    assert meta["count"] == 3
    assert meta["driver"] == "JPEG"

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

    # region=Invalid
    response = app.get(f"/iiif/{identifier}/pct:105,100,100,100/max/0/default.jpg")
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
    # QUALITY
    response = app.get(f"/iiif/{identifier}/full/max/0/gray.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1000
    assert meta["height"] == 695
    assert meta["count"] == 1

    response = app.get(f"/iiif/{identifier}/full/max/0/bitonal.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1000
    assert meta["height"] == 695
    assert meta["count"] == 1

    response = app.get(f"/iiif/{identifier}/full/max/0/color.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1000
    assert meta["height"] == 695
    assert meta["count"] == 3

    ###########################################################################
    # SIZE
    # size: ^max (upscale to server maxwidth: 2000)
    response = app.get(f"/iiif/{identifier}/full/^max/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 2000
    assert meta["height"] == 1390

    # size: pct:n
    response = app.get(f"/iiif/{identifier}/full/pct:50/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 500
    assert meta["height"] == 348

    # size: pct invalid
    response = app.get(f"/iiif/{identifier}/full/pct:-50/0/default.jpg")
    assert response.status_code == 400

    response = app.get(f"/iiif/{identifier}/full/^pct:-50/0/default.jpg")
    assert response.status_code == 400

    # do not allow upscale without ^
    response = app.get(f"/iiif/{identifier}/full/pct:150/0/default.jpg")
    assert response.status_code == 400

    # size: ^pct:n
    response = app.get(f"/iiif/{identifier}/full/^pct:150/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1500
    assert meta["height"] == 1042

    # size: ^pct:n but limit to server limit
    response = app.get(f"/iiif/{identifier}/full/^pct:300/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 2000
    assert meta["height"] == 1390

    # size: w,
    response = app.get(f"/iiif/{identifier}/full/500,/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 500
    assert meta["height"] == 348

    # Do not allow upscale
    response = app.get(f"/iiif/{identifier}/full/1500,/0/default.jpg")
    assert response.status_code == 400

    # size: ^w,
    response = app.get(f"/iiif/{identifier}/full/^1500,/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1500
    assert meta["height"] == 1042

    # size: ,h
    response = app.get(f"/iiif/{identifier}/full/,348/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 501
    assert meta["height"] == 348

    # Do not allow upscale
    response = app.get(f"/iiif/{identifier}/full/,1042/0/default.jpg")
    assert response.status_code == 400

    # size: ^,h
    response = app.get(f"/iiif/{identifier}/full/^,1042/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1499
    assert meta["height"] == 1042

    # size: w,h
    response = app.get(f"/iiif/{identifier}/full/100,50/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 100
    assert meta["height"] == 50

    # Do not allow upscale
    response = app.get(f"/iiif/{identifier}/full/1500,1000/0/default.jpg")
    assert response.status_code == 400

    # size: ^w,h
    response = app.get(f"/iiif/{identifier}/full/^1500,1000/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1500
    assert meta["height"] == 1000

    # size: !w,h (maintain aspect ratio)
    response = app.get(f"/iiif/{identifier}/full/!750,800/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 750
    assert meta["height"] == 521

    # Do not allow upscale
    response = app.get(f"/iiif/{identifier}/full/!1500,800/0/default.jpg")
    assert response.status_code == 400

    # size: ^!w,h (maintain aspect ratio)
    response = app.get(f"/iiif/{identifier}/full/^!1500,800/0/default.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpg"
    meta = parse_img(response.content)
    assert meta["width"] == 1500
    assert meta["height"] == 1042

    # size: invalid
    response = app.get(f"/iiif/{identifier}/full/^!0,0/0/default.jpg")
    assert response.status_code == 400

    response = app.get(f"/iiif/{identifier}/full/0,0/0/default.jpg")
    assert response.status_code == 400

    response = app.get(f"/iiif/{identifier}/full/^0,0/0/default.jpg")
    assert response.status_code == 400

    response = app.get(f"/iiif/{identifier}/full/0,/0/default.jpg")
    assert response.status_code == 400

    response = app.get(f"/iiif/{identifier}/full/^0,/0/default.jpg")
    assert response.status_code == 400

    response = app.get(f"/iiif/{identifier}/full/^,0/0/default.jpg")
    assert response.status_code == 400

    response = app.get(f"/iiif/{identifier}/full/,0/0/default.jpg")
    assert response.status_code == 400
