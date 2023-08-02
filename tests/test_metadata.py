"""test metadata Factory endpoints."""

import os

PREFIX = os.path.join(os.path.dirname(__file__), "fixtures")

boston_jpeg = os.path.join(PREFIX, "boston.jpg")
cog_gcps = os.path.join(PREFIX, "cog_gcps.tif")


def test_info(app):
    """test /info endpoint."""
    response = app.get("/info", params={"url": boston_jpeg})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    expected = {
        "bounds": [0, 5352, 7696, 0],
        "minzoom": 0,
        "maxzoom": 5,
        "band_metadata": [["b1", {}], ["b2", {}], ["b3", {}]],
        "band_descriptions": [["b1", ""], ["b2", ""], ["b3", ""]],
        "dtype": "uint8",
        "nodata_type": "None",
        "colorinterp": ["red", "green", "blue"],
        "driver": "JPEG",
        "count": 3,
        "width": 7696,
        "height": 5352,
        "overviews": [2, 4, 8],
    }
    assert body == expected

    response = app.get("/info", params={"url": cog_gcps})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    expected = {
        "bounds": [0, 837, 1280, 0],
        "minzoom": 0,
        "maxzoom": 2,
        "band_metadata": [["b1", {}]],
        "band_descriptions": [["b1", ""]],
        "dtype": "uint16",
        "nodata_type": "None",
        "colorinterp": ["gray"],
        "driver": "GTiff",
        "count": 1,
        "width": 1280,
        "height": 837,
        "overviews": [2, 4, 8],
    }
    assert body == expected


def test_statistics(app):
    """test /statistics endpoint."""
    response = app.get("/statistics", params={"url": boston_jpeg})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    expected = {
        "b1": {
            "min": 0.0,
            "max": 255.0,
            "mean": 220.9768487574509,
            "count": 730112.0,
            "sum": 161337849.0,
            "std": 40.5618108485455,
            "median": 234.0,
            "majority": 237.0,
            "minority": 248.0,
            "unique": 256.0,
            "histogram": [
                [16434, 1237, 1655, 2135, 3594, 6181, 16975, 44742, 143524, 493635],
                [
                    0.0,
                    25.5,
                    51.0,
                    76.5,
                    102.0,
                    127.5,
                    153.0,
                    178.5,
                    204.0,
                    229.5,
                    255.0,
                ],
            ],
            "valid_percent": 100.0,
            "masked_pixels": 0.0,
            "valid_pixels": 730112.0,
            "percentile_2": 6.0,
            "percentile_98": 241.0,
        },
        "b2": {
            "min": 0.0,
            "max": 236.0,
            "mean": 208.6166697712132,
            "count": 730112.0,
            "sum": 152313534.0,
            "std": 38.8684106948778,
            "median": 221.0,
            "majority": 227.0,
            "minority": 236.0,
            "unique": 237.0,
            "histogram": [
                [16567, 1221, 1418, 1916, 2693, 5897, 17909, 45820, 117856, 518815],
                [
                    0.0,
                    23.6,
                    47.2,
                    70.80000000000001,
                    94.4,
                    118.0,
                    141.60000000000002,
                    165.20000000000002,
                    188.8,
                    212.4,
                    236.0,
                ],
            ],
            "valid_percent": 100.0,
            "masked_pixels": 0.0,
            "valid_pixels": 730112.0,
            "percentile_2": 4.0,
            "percentile_98": 231.0,
        },
        "b3": {
            "min": 0.0,
            "max": 226.0,
            "mean": 190.8284715221774,
            "count": 730112.0,
            "sum": 139326157.0,
            "std": 38.205110269611204,
            "median": 205.0,
            "majority": 211.0,
            "minority": 226.0,
            "unique": 227.0,
            "histogram": [
                [16882, 1275, 1427, 2638, 4872, 13681, 40667, 71072, 193921, 383677],
                [
                    0.0,
                    22.6,
                    45.2,
                    67.80000000000001,
                    90.4,
                    113.0,
                    135.60000000000002,
                    158.20000000000002,
                    180.8,
                    203.4,
                    226.0,
                ],
            ],
            "valid_percent": 100.0,
            "masked_pixels": 0.0,
            "valid_pixels": 730112.0,
            "percentile_2": 5.0,
            "percentile_98": 218.0,
        },
    }
    assert body == expected

    response = app.get(
        "/statistics",
        params={
            "url": boston_jpeg,
            "bidx": 1,
            "histogram_bins": 5,
            "histogram_range": "0,100",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    expected = {
        "b1": {
            "min": 0.0,
            "max": 255.0,
            "mean": 220.9768487574509,
            "count": 730112.0,
            "sum": 161337849.0,
            "std": 40.5618108485455,
            "median": 234.0,
            "majority": 237.0,
            "minority": 248.0,
            "unique": 256.0,
            "histogram": [
                [16216, 864, 1247, 1163, 1875],
                [0.0, 20.0, 40.0, 60.0, 80.0, 100.0],
            ],
            "valid_percent": 100.0,
            "masked_pixels": 0.0,
            "valid_pixels": 730112.0,
            "percentile_2": 6.0,
            "percentile_98": 241.0,
        }
    }
    assert body == expected
