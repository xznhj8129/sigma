"""
Usage:
    python examples/spatial_schemas.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "sdk" / "sigmac3-sdk"))

from sigmac3_sdk.core.schema import (
    GeoJsonFeature,
    GeoJsonFeatureCollection,
    GeoJsonGeometry,
    Wgs84Location,
)


if __name__ == "__main__":
    observation = Wgs84Location(
        lat=34.1234,
        lon=-117.1234,
        alt=1500.0,
        mgrs="11SLT1234567890",
    )
    point_geometry = GeoJsonGeometry(
        type="Point",
        coordinates=[observation.lon, observation.lat, observation.alt],
    )
    feature = GeoJsonFeature(
        geometry=point_geometry,
        properties={"name": "Sample site", "mgrs": observation.mgrs},
    )
    collection = GeoJsonFeatureCollection(features=[feature])

    print("GeoJSON Feature:")
    print(feature.model_dump_json(indent=2))
    print("GeoJSON FeatureCollection:")
    print(collection.model_dump_json(indent=2))
