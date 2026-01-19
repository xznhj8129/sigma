from enum import Enum


NATO_ALPHABET = (
    "ALPHA",
    "BRAVO",
    "CHARLIE",
    "DELTA",
    "ECHO",
    "FOXTROT",
    "GOLF",
    "HOTEL",
    "INDIA",
    "JULIETT",
    "KILO",
    "LIMA",
    "MIKE",
    "NOVEMBER",
    "OSCAR",
    "PAPA",
    "QUEBEC",
    "ROMEO",
    "SIERRA",
    "TANGO",
    "UNIFORM",
    "VICTOR",
    "WHISKEY",
    "XRAY",
    "YANKEE",
    "ZULU",
)


class SchemaKind(str, Enum):
    BASIC_UNIT = "basic_unit"
    GROUND_ORG = "ground_org"
    AIR_ORG = "air_org"
    AIR_UNIT = "air_unit"
    GROUND_UNIT = "ground_unit"
    INTEL_TRACK = "intel_track"
    LINK = "link"
    SENSOR = "sensor"


class UnitSize(str, Enum):
    IND = "IND"
    TEM = "TEM"
    SQD = "SQD"
    SEC = "SEC"
    PLT = "PLT"
    COY = "COY"
    BTN = "BTN"
    RGT = "RGT"
    BDE = "BDE"
    DIV = "DIV"
    FLT = "FLT"
    SQN = "SQN"
    GRP = "GRP"
    WNG = "WNG"


UNIT_SIZE_LABELS = {
    UnitSize.IND: "Individual",
    UnitSize.TEM: "Team",
    UnitSize.SQD: "Squad",
    UnitSize.SEC: "Section",
    UnitSize.PLT: "Platoon",
    UnitSize.COY: "Company",
    UnitSize.BTN: "Battalion",
    UnitSize.RGT: "Regiment",
    UnitSize.BDE: "Brigade",
    UnitSize.DIV: "Division",
    UnitSize.FLT: "Flight",
    UnitSize.SQN: "Squadron",
    UnitSize.GRP: "Group",
    UnitSize.WNG: "Wing",
}


class UnitCategory(str, Enum):
    COMB = "COMB"
    BATT = "BATT"
    TF = "TF"
    MECH = "MECH"
    INF = "INF"
    MOT = "MOT"
    REC = "REC"
    UAV = "UAV"
    UAVA = "UAVA"
    UAVR = "UAVR"
    UGV = "UGV"
    SIG = "SIG"
    ENG = "ENG"
    ART = "ART"
    MORT = "MORT"
    MRL = "MRL"
    ARM = "ARM"
    CAV = "CAV"
    MED = "MED"
    SUP = "SUP"
    LOG = "LOG"
    HQ = "HQ"
    NBC = "NBC"
    MP = "MP"
    AIR = "AIR"
    SOF = "SOF"
    NAV = "NAV"
    AMP = "AMP"
    ADA = "ADA"
    EW = "EW"
    ISR = "ISR"
    CBT = "CBT"
    CSS = "CSS"
    COM = "COM"
    DET = "DET"
    RES = "RES"
    TRG = "TRG"


UNIT_CATEGORY_LABELS = {
    UnitCategory.COMB: "Combined Arms",
    UnitCategory.BATT: "Battery",
    UnitCategory.TF: "Task Force",
    UnitCategory.MECH: "Mechanized Infantry",
    UnitCategory.INF: "Light Infantry",
    UnitCategory.MOT: "Motorized Infantry",
    UnitCategory.REC: "Reconnaissance",
    UnitCategory.UAV: "Unmanned Aerial Systems",
    UnitCategory.UAVA: "UAV Attack",
    UnitCategory.UAVR: "UAV Recon",
    UnitCategory.UGV: "Unmanned Ground Systems",
    UnitCategory.SIG: "Signal",
    UnitCategory.ENG: "Engineer",
    UnitCategory.ART: "Artillery",
    UnitCategory.MORT: "Mortar",
    UnitCategory.MRL: "Rocket Artillery",
    UnitCategory.ARM: "Armored",
    UnitCategory.CAV: "Cavalry",
    UnitCategory.MED: "Medical",
    UnitCategory.SUP: "Supply",
    UnitCategory.LOG: "Logistics",
    UnitCategory.HQ: "Headquarters",
    UnitCategory.NBC: "Nuclear, Biological, and Chemical Defense",
    UnitCategory.MP: "Military Police",
    UnitCategory.AIR: "Airborne Infantry",
    UnitCategory.SOF: "Special Operations Forces",
    UnitCategory.NAV: "Naval Infantry",
    UnitCategory.AMP: "Amphibious Infantry",
    UnitCategory.ADA: "Air Defense Artillery",
    UnitCategory.EW: "Electronic Warfare",
    UnitCategory.ISR: "Intelligence, Surveillance, and Reconnaissance",
    UnitCategory.CBT: "Combat Support",
    UnitCategory.CSS: "Combat Service Support",
    UnitCategory.COM: "Command",
    UnitCategory.DET: "Detachment",
    UnitCategory.RES: "Reserve",
    UnitCategory.TRG: "Training",
}


class AirRole(str, Enum):
    GROUND = "G"
    AIR_DEFENSE = "AA"
    FIGHTER = "F"
    RECON = "R"
    IMINT = "I"
    SIGINT = "S"
    MINE = "L"
    CARGO = "C"


AIR_ROLE_LABELS = {
    AirRole.GROUND: "Ground Attack",
    AirRole.AIR_DEFENSE: "Anti-Air",
    AirRole.FIGHTER: "Anti-Air",
    AirRole.RECON: "Reconnaissance",
    AirRole.IMINT: "IMINT",
    AirRole.SIGINT: "SIGINT",
    AirRole.MINE: "Minelaying",
    AirRole.CARGO: "Cargo",
}
