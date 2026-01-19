from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Position(BaseModel):
    lat: float
    lon: float
    alt: float

    model_config = ConfigDict(extra="forbid")


class AreaOfOperations(BaseModel):
    shape: str
    points: list[tuple[float, float]]
    size: float

    model_config = ConfigDict(extra="forbid")


class WeatherLimits(BaseModel):
    ifr: bool | None = None
    rain: float | None = None
    snow: float | None = None
    temp: tuple[float, float] | None = None
    wind: float | None = None
    vis: float | None = None
    icing: bool | None = None

    model_config = ConfigDict(extra="forbid")


class SpotterOrigin(BaseModel):
    lat: float
    lon: float
    pitch: float
    heading: float
    bearing: float
    elevation: float
    range: float

    model_config = ConfigDict(extra="forbid")


class SensorSchema(BaseModel):
    name: str
    model: str
    type: str
    serial_uid: str
    effect_domain: str
    max_range: float
    ptz: bool
    spectrum: str
    night_vision: bool
    all_weather: bool
    weather_limits: dict[str, Any]
    error_margin: float
    error_type: str
    data_formats: list[Any]
    ai: list[Any]
    datalink: str
    fov: list[Any]
    zoom_range: list[Any]

    model_config = ConfigDict(extra="forbid")


class LinkSchema(BaseModel):
    template_id: str
    template_type: str
    uuid: str
    name: str
    link_type: str
    net_type: str
    io: int
    data_type: str
    rxtx: str
    bands: dict[str, Any]
    waveform: str
    bandwidth: dict[str, Any] | None = None
    speed: dict[str, Any] | None = None
    user_capacity: dict[str, Any] | None = None
    freq_set: float
    ch: list[Any]
    ch_set: float
    crypto_type: list[Any]
    crypto_set: list[Any]
    crypto_keys: dict[str, Any]
    net_set: str
    ip: str

    model_config = ConfigDict(extra="forbid")


class TemplatePathMap(BaseModel):
    ground_org: Path
    air_units: Path
    links: Path

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
