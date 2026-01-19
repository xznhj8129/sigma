import random
import uuid

from flask import jsonify

from sigmac3_sdk.core.schema import UNIT_CATEGORY_NAMES, UNIT_SIZE_LABELS
from sigmac3_sdk.geo import GPSposition


def randcode(n: int) -> str:
    return "".join(random.choices("0123456789", k=n))


CATEGORY_LABELS = {k.value: v for k, v in UNIT_CATEGORY_NAMES.items()}
SIZE_LABELS = {k.value: v for k, v in UNIT_SIZE_LABELS.items()}


class CabalUnit:
    def __old_init__(self):
        self.name = ""
        self.full_name = ""
        self.callsign = ""
        self.num = 0
        self.unit_code = randcode(8)
        self.uid = str(uuid.uuid4())
        self.domain = 0         # Ground, Air, Sea
        self.status = 0         # Present, Damaged, Xdestroyed, Lost, Decoy/fake
        self.commander = "AI"
        self.description = ""

        self.category = ""
        self.personnel = -1     # -1 = unmanned/N/A, 0 = destroyed, >1 normal
        self.sizelevel = 0      # enumLandUnitSizes
        self.infantry = 0
        self.size= ""           # org type name (squad, battalion, etc)
        self.taskforce = False  # changes size classification and orbat
        self.levels_up = 0
        self.orglevel = 0
        self.cot = ""
        self.sidc = ""

        self.sensors = {}
        self.weapons = {}
        self.ammo = {}
        self.ordnance = {}
        self.resupply = {}
        self.area_operations = {"shape": "circle",  "points": [(0,0)], "size": 100}

        self.parent = ""        # organizational superior unit
        self.parent_num = 0
        self.grandparent = ""   # superior of superior
        self.grandparent_num = 0
        self.attached = False   # is attached to non-parent
        self.attached_to = ""   # teporary attachment superior unit
        self.attachments = {}   # non-integral attachments

        self.position = GPSposition(0,0,0)
        self.ang = (0,0) #heading, pitch
        self.vel = (0,0) #h speed, v speed

        self.tac_elements = {}
        self.sup_elements = {}
        self.tac_e_comp = {}
        self.sup_e_comp = {}
        self.equipment= {}
        self.vehicles = {}
        self.air_units= {}

        self.operation= ""
        self.task= ""
        self.opord = ""
        self.plan= ""
        self.orders= ""
        self.links= {}
    
    def __init__(
        self,
        template_type=None,
        unit_template=None,
        uid="",
        code="",
    ):
        self.template_type = template_type
        self.unit_code = code or randcode(8)
        self.uid = uid or str(uuid.uuid4())

        if unit_template:
            self.define(template_type=template_type, unit_template=unit_template, uid=uid, code=code)

    def define(
        self,
        template_type=None,
        unit_template=None,
        uid="",
        code="",
    ):
        if unit_template:
            for i in unit_template:
                setattr(self, i, unit_template[i])

        if template_type:
            self.template_type = template_type

        self.unit_code = code or randcode(8)
        self.uid = uid or str(uuid.uuid4())
    
    def from_json(self, jsonobj):
        self.__old_init__()
        for i in jsonobj:
            if i=="position":
                pos = jsonobj[i]
                if type(pos) == dict:
                    setattr(self, i, GPSposition(pos['lat'],pos['lon'],pos['alt']))
                elif type(pos) == list:
                    setattr(self, i, GPSposition(pos[0],pos[1],0))
            else:
                setattr(self, i, jsonobj[i])
        self.get_name()

    def json(self):
        return jsonify(self)

    def as_dict(self):
        return self.__dict__

    def get_name(self):
        if self.taskforce:
            self.name = f"{self.category} {self.size} TF {self.callsign} ({self.unit_code})"
        else:
            self.name = f"{self.num} {self.category} {self.size} {self.callsign} ({self.unit_code})"
        return self.name

    def get_full_name(self):
        if self.taskforce:
            self.name = f"{CATEGORY_LABELS[self.category]} {SIZE_LABELS[self.size]} Task Force {self.callsign} ({self.unit_code})"
        else:
            self.name = f"{self.num} {CATEGORY_LABELS[self.category]} {SIZE_LABELS[self.size]} {self.callsign} ({self.unit_code})"
        return self.name

    def set_callsign(self, callsign=None, parent=None, grandparent=None, greatgrandp=None):
        # this is sketchy
        if parent:
            shifted = self.sizelevel + (parent.levels_up-2)
        else:
            shifted = self.sizelevel

        if self.taskforce and callsign:
            self.callsign = callsign

        elif callsign and shifted<5 and not grandparent and not self.taskforce:
            self.callsign = f"{callsign}-{self.num}"
        elif shifted<= 3: #SEC/SQD/TEM
            self.callsign = f"{grandparent.callsign}-{parent.num}-{self.num}"
        elif shifted == 4: #PLT
            self.callsign = f"{parent.callsign}-{self.num}"
        elif shifted == 5: #COY
            if parent:
                self.callsign = f"{callsign}-{parent.num}BTN"
            else:
                self.callsign = callsign
        elif shifted == 6: # BTN
            self.callsign = f"{self.num}BTN-{parent.num}RGT"
        elif shifted == 7: # RGT
            self.callsign = f"{self.num}RGT-{parent.num}BDE"
        elif shifted == 8: # BDE
            self.callsign = f"{self.num}BDE"
        elif shifted == 9: # DIV
            self.callsign = f"{self.num}DIV"

    def printed_orbat(self):
        pass

    def get_centroid(self):
        pass

class ExternalFormation(CabalUnit):
    def __init__(self, faction=None, 
        template_type=None, 
        unit_template=None,
        code=None ):
        super().__init__(template_type=template_type, unit_template=unit_template, code=code)
        self.faction = "UNKNOWN" if not faction else faction

    def get_name(self):
        if self.taskforce:
            name = f"{self.faction} {self.category} {self.size} TF {self.callsign} ({self.unit_code})"
        else:
            name = f"{self.faction} {self.num} {self.category} {self.size} {self.callsign} ({self.unit_code})"
        return name

class IntelTrack(CabalUnit):
    def __init__(self, faction=None, 
        template_type=None, 
        unit_template=None,
        code=None ):
        super().__init__(template_type=template_type, unit_template=unit_template, code=code)
        self.faction = "UNKNOWN" if not faction else faction
