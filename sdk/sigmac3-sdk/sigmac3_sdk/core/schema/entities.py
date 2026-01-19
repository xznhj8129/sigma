from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import AirRole, SchemaKind, UnitCategory, UnitSize
from .models import WeatherLimits, SpotterOrigin


class BaseEntity(BaseModel):
    template_id: str
    template_type: SchemaKind

    model_config = ConfigDict(extra="forbid")


class BaseUnit(BaseEntity):
    category: UnitCategory | str | None = None
    size: UnitSize | str | None = None
    sizelevel: int | None = None
    taskforce: bool | None = None
    sidc: str | None = None
    cot: str | None = None

    model_config = ConfigDict(extra="forbid")


class PersonnelSchema(BaseEntity):
    model: str
    role: str
    serial_uid: str
    propulsion: str
    attack_modes: list[str]
    sensors: dict[str, Any]
    weapons: dict[str, Any]
    ammo: dict[str, Any]
    health: str
    status: str
    links: dict[str, Any]
    navigation: str
    navaids: dict[str, Any]
    model_config = ConfigDict(extra="forbid")

class GroundOrganizationSchema(BaseUnit):
    category: UnitCategory
    size: UnitSize
    sizelevel: int
    taskforce: bool
    tac_e_comp: dict[str, int]
    sup_e_comp: dict[str, int]
    links: dict[str, int]
    equipment: dict[str, int]
    personnel: int
    infantry: int
    vehicles: dict[str, int]
    air_units: dict[str, int]
    spacing: float
    ammo: dict[str, int]
    weapons: dict[str, int]
    sidc: str

    model_config = ConfigDict(extra="forbid")


class AirUnitSchema(BaseUnit):
    model: str
    type: str
    serial_uid: str
    propulsion: str
    reusable: bool
    has_warhead: bool
    warhead: str
    has_launchers: bool
    attack_modes: list[str]
    pylons: str
    flight_type: str
    launcher: str
    pylon_format: str
    launch_domain: str
    effect_domain: str
    sensors: list[str]
    rc_link: str
    vid_link: str
    ctrl_video_sep: bool
    ordnance: dict[str, Any]
    guidance: str
    navigation: str
    navaids: list[str]
    autopilot: bool
    autopilot_model: str
    autopilot_fw: dict[str, Any] = Field(alias="autopiot_fw")
    fuel_type: str
    fuel_config: dict[str, Any]
    fuel_cons: dict[str, Any]
    control_modes: list[str]
    max_range: float
    max_flight_t: float
    max_spd: float
    cruise_spd: float
    max_alt: float
    start_flight_time: float
    status: str
    maint_status: dict[str, Any]
    weather_limits: WeatherLimits
    ifr: bool | None = None
    roles: list[AirRole]
    links: dict[str, Any]
    weapons: dict[str, Any]
    ammo: dict[str, Any]

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class GroundUnitSchema(BaseUnit):
    model: str
    role: str
    serial_uid: str
    status: str
    propulsion: str
    has_launchers: bool
    attack_modes: list[str]
    pylons: str
    max_range: float
    sensors: dict[str, Any]
    weapons: dict[str, Any]
    ammo: dict[str, Any]
    links: dict[str, Any]
    ordnance: dict[str, Any]
    navigation: str
    navaids: dict[str, Any]
    control_modes: list[str]
    max_spd: float

    model_config = ConfigDict(extra="forbid")

class AirOrganizationSchema(BaseUnit):
    tac_elements: dict[str, Any]
    sup_elements: dict[str, Any]
    tac_e_comp: dict[str, int]
    sup_e_comp: dict[str, int]
    personnel: int
    vehicles: dict[str, int]
    equipment: dict[str, int]
    air_units: dict[str, int]
    spacing: float

    model_config = ConfigDict(extra="forbid")


class IntelTrackSchema(BaseEntity):
    faction: str
    spotted_time: float
    updated_time: float
    stale_time: float
    spotter_origin: SpotterOrigin
    spotter_last: dict[str, Any]
    history: list[Any]
    error_m: float

    model_config = ConfigDict(extra="forbid")
