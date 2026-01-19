from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GeoJsonGeometry(BaseModel):
    type: Literal[
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    ]
    coordinates: Any | None
    geometries: list["GeoJsonGeometry"] | None = None
    bbox: list[float] | None = None

    model_config = ConfigDict(extra="forbid")


class GeoJsonFeature(BaseModel):
    type: Literal["Feature"] = Field(default="Feature", frozen=True)
    geometry: GeoJsonGeometry
    properties: dict[str, Any]
    id: str | int | None = None
    bbox: list[float] | None = None

    model_config = ConfigDict(extra="forbid")


class GeoJsonFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = Field(
        default="FeatureCollection",
        frozen=True,
    )
    features: list[GeoJsonFeature]
    bbox: list[float] | None = None

    model_config = ConfigDict(extra="forbid")


class Wgs84Location(BaseModel):
    lat: float
    lon: float
    alt: float | None = None
    mgrs: str | None = None
    datum: Literal["WGS84"] = Field(default="WGS84", frozen=True)

    model_config = ConfigDict(extra="forbid")


GeoJsonGeometry.model_rebuild()
