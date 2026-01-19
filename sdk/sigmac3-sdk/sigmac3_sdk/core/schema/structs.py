from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from .enums import NATO_ALPHABET, UNIT_CATEGORY_LABELS, UNIT_SIZE_LABELS, AirRole, UnitSize


UNIT_SIZE_LEVELS_LAND: Mapping[UnitSize, int] = {
    UnitSize.IND: 0,
    UnitSize.TEM: 1,
    UnitSize.SQD: 2,
    UnitSize.SEC: 3,
    UnitSize.PLT: 4,
    UnitSize.COY: 5,
    UnitSize.BTN: 6,
    UnitSize.RGT: 7,
    UnitSize.BDE: 8,
    UnitSize.DIV: 9,
}

UNIT_SIZE_LEVELS_AIR: Mapping[UnitSize, int] = {
    UnitSize.IND: 0,
    UnitSize.TEM: 1,
    UnitSize.FLT: 2,
    UnitSize.SQN: 3,
    UnitSize.GRP: 4,
    UnitSize.WNG: 5,
}

UNIT_SIZE_SHORT = UNIT_SIZE_LABELS
UNIT_CATEGORY_NAMES = UNIT_CATEGORY_LABELS

CALLSIGN_TEMPLATES: Mapping[UnitSize, str] = {
    UnitSize.SQD: "<coy_callsign>-<plt_num>-<s_num>",
    UnitSize.SEC: "<coy_callsign>-<plt_num>-<s_num>",
    UnitSize.PLT: "<coy_callsign>-<plt_num>",
    UnitSize.COY: "<coy_callsign>-<btn_num>BTN",
    UnitSize.BTN: "<btn_num>BTN-<rgt_num>RGT",
    UnitSize.RGT: "<rgt_num>RGT-<bde_num>BDE",
    UnitSize.BDE: "<bde_num>BDE",
    UnitSize.TF: "<tf_name>",
} if hasattr(UnitSize, "TF") else {
    UnitSize.SQD: "<coy_callsign>-<plt_num>-<s_num>",
    UnitSize.SEC: "<coy_callsign>-<plt_num>-<s_num>",
    UnitSize.PLT: "<coy_callsign>-<plt_num>",
    UnitSize.COY: "<coy_callsign>-<btn_num>BTN",
    UnitSize.BTN: "<btn_num>BTN-<rgt_num>RGT",
    UnitSize.RGT: "<rgt_num>RGT-<bde_num>BDE",
    UnitSize.BDE: "<bde_num>BDE",
}

ENEMY_CALLSIGN_TEMPLATES = CALLSIGN_TEMPLATES

AIR_ROLE_NAMES: Mapping[AirRole, str] = {
    AirRole.GROUND: "Ground Attack",
    AirRole.AIR_DEFENSE: "Air Defense",
    AirRole.FIGHTER: "Anti-Air",
    AirRole.RECON: "Reconnaissance",
    AirRole.IMINT: "IMINT",
    AirRole.SIGINT: "SIGINT",
    AirRole.MINE: "Minelaying",
    AirRole.CARGO: "Cargo",
}


class BdaReportTemplate(BaseModel):
    time: float = 0.0
    uid: str = ""
    unit_code: str = ""
    spotter: str = ""
    track: str = ""
    sensor: str = ""
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    casualties: int = 0
    destroyed: dict[str, Any] = Field(default_factory=dict)
    damaged: dict[str, Any] = Field(default_factory=dict)
    unknown: dict[str, Any] = Field(default_factory=dict)
    description: str = ""

    model_config = ConfigDict(extra="forbid")


class SaluteReportTemplate(BaseModel):
    time: float = 0.0
    uid: str = ""
    unit_code: str = ""
    spotter: str = ""
    sensor: str = ""
    spotter_pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    activity: str = ""
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    equipment: list[str] = Field(default_factory=list)
    vehicles: list[str] = Field(default_factory=list)
    description: str = ""

    model_config = ConfigDict(extra="forbid")


SIDC_FACTION = {
    "UNKNOWN": "U",
    "PENDING": "P",
    "FRIENDLY": "F",
    "SUSPECT": "S",
    "HOSTILE": "H",
    "NEUTRAL": "N",
}

SIDC_DOMAIN = {
    "ground": "G",
    "air": "A",
    "sea": "S",
    "sub": "U",
}

SIDC_STATUS = {
    "anticipated": "A",
    "present": "P",
    "present-capable": "C",
    "present-damaged": "D",
    "present-destroyed": "X",
}

SIDC_AIR_A5 = {
    "track": "-",
    "military": "M",
    "civilian": "C",
}

SIDC_AIR_A6 = {
    "fixed-wing": "F",
    "rotary": "H",
    "weapon": "W",
}

SIDC_AIR_MILITARY = {
    "fighter": "F",
    "attack": "A",
    "bomber": "B",
    "utility": "U",
    "drone": "Q",
    "missile": "M",
    "decoy": "D",
    "recon": "R",
    "ecm": "J",
}

SIDC_GROUND_A5 = {
    "track": "-",
    "unit": "U",
}

SIDC_GROUND_A6 = {
    "combat": "C",
    "combat-support": "U",
    "service-support": "S",
}

SIDC_COMBAT_GROUND = {
    "air-defence": "D",
    "armor": "A",
    "ssm": "M",
    "artillery": "F",
    "infantry": "I",
    "anti-tank": "A",
    "recon": "R",
    "hq": "H",
    "engineer": "E",
}

SIDC_COMBAT_GROUND_INFANTRY = {
    "light": "L",
    "motorized": "M",
    "mechanized": "Z",
    "ifv": "I",
    "air-assault": "A",
}

SIDC_AIR_WEAPON_MISSILE = {
    "ssm": "S*APWMSS----",
    "sam": "S*APWMSA----",
    "aam": "S*APWMAA----",
    "asm": "S*APWMAS----",
    "land-attack": "S*APWML----",
}

SIDC_GROUND_ARTILLERY = {
    "spg": "S*GPUCFHE---",
    "light_towed": "S*GPUCFHL---",
    "medium_towed": "S*GPUCFHM---",
    "heavy_towed": "S*GPUCFHH---",
    "sp_mrl": "S*GPUCFRMS--",
    "towed_mortar": "S*GPUCFMT---",
    "ssm": "S*GPUCMMT---",
}

SIDC_UNIT_SIZE = {
    "single": "-",
    "team": "A",
    "squad": "B",
    "section": "C",
    "platoon": "D",
    "company": "E",
    "battalion": "F",
    "regiment": "G",
    "brigade": "H",
    "division": "H",
}

SIDC_CODES = {
    "friendly": {
        "land": {
            "default": "S*GP--------",
            "unit": "S*GPUC------",
            "infantry": "S*GPUCI-----",
            "armor": "S*GPUCA-----",
            "recon": "S*GPUCR-----",
            "artillery": "S*GPUCF-----",
            "hq": "S*GPUH----A-",
            "tfhq": "S*GPUH----B-",
            "tf": "S*GPUH----E-",
        },
        "air": {
            "default": "S*APM-------",
        },
    },
    "hostile": {
        "land": {
            "default": "SHGPU-------",
        },
        "air": {
            "default": "SHAPM-------",
        },
    },
}
