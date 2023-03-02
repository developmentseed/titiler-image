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

![](https://user-images.githubusercontent.com/10407788/222417904-98b2dc2b-3e4d-43cf-a883-9dc2355f81f4.png)

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

## Contribution & Development

See [CONTRIBUTING.md](https://github.com//developmentseed/titiler-image/blob/main/CONTRIBUTING.md)

## License

See [LICENSE](https://github.com//developmentseed/titiler-image/blob/main/LICENSE)

## Authors

See [contributors](https://github.com/developmentseed/titiler-image/graphs/contributors) for a listing of individual contributors.

## Changes

See [CHANGES.md](https://github.com/developmentseed/titiler-image/blob/main/CHANGES.md).
