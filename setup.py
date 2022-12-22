"""Setup titiler.image."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    long_description = f.read()

inst_reqs = [
    "titiler.core>=0.10.2,<0.11",
    "starlette-cramjam>=0.3,<0.4",
    "python-dotenv",
]
extra_reqs = {
    "dev": ["pre-commit"],
    "test": [
        "pytest",
        "pytest-cov",
        "pytest-asyncio",
        "httpx",
    ],
}

setup(
    name="titiler.image",
    description="Connect PgSTAC and TiTiler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="DeepZoom TiTiler FastAPI",
    author="Vincent Sarago",
    author_email="vincent@developmentseed.org",
    url="https://github.com/developmentseed/titiler-image",
    license="MIT",
    packages=find_namespace_packages(exclude=["tests*"]),
    package_data={"titiler": ["image/templates/*.html"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
