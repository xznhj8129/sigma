import sys
from pathlib import Path

from setuptools import find_packages, setup

if sys.version_info < (3, 9):
    sys.exit("Sorry, Python < 3.9 is not supported.")

README_PATH = Path(__file__).parent / "README.md"
setup(
    name="sigmac3-sdk",
    packages=find_packages(include=["sigmac3_sdk", "sigmac3_sdk.*"]),
    version="0.1.0",
    license="GPL",
    description="Sigma C4ISR core schemas, geo utilities, and transport clients",
    long_description=README_PATH.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Sigma",
    author_email="",
    url="https://github.com",
    include_package_data=True,
    keywords=["c4isr", "cot", "atak", "geo", "schemas", "sdk"],
    install_requires=[
        "pydantic>=2.6",
        "requests>=2.31",
        "geographiclib",
        "geojson",
        "mgrs",
        "numpy",
        "pandas",
        "flask",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: GIS",
    ],
)
