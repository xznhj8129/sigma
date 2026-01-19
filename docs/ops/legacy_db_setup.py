"""
Legacy DB seeding example (expects legacy template files that are no longer shipped).
Retained for reference.
"""
# example_usage.py
from sigmac3_sdk.core import *
from sigmac3_sdk.clients import DBClient
from sigmac3_sdk.geo import *
from frogcot import *

units = {}
enemy_units = {}

client = DBClient(base_url="http://localhost:5001")
with open("templates/units.json","r") as file:
    unit_templates = json.loads(file.read())
with open("templates/basic_templates.json","r") as file:
    basic_templates = json.loads(file.read())


def addunit(unit_template,  # the full json
    num, 
    callsign=None, 
    name=None, 
    parent=None, 
    grandparent=None, 
    pos=None, 
    code=None, 
    faction=None
    ):
    global unit_templates
    global basic_templates
    global units
    print(unit_template)

    ttype = unit_template["template_type"]
    unit = CabalUnit(unit_template=unit_template, code=code )
    #if code: unit.unit_code = code
    if name: unit.name = name
    unit.num = num

    unit.parent = parent.unit_code if parent else None

    if pos and parent:
        unit.position = vector_to_gps(parent.position, unit.spacing, random.randrange(0,360))
    elif pos:
        unit.position = pos

    if parent:
        unit.orglevel = parent.orglevel + 1
    else:
        unit.orglevel = 0

    # this is fucked
    if unit.category == "HQ":
        unit.callsign = f"{parent.callsign}-HQ"
    elif unit.orglevel == 0:
        unit.callsign = callsign
    elif unit.orglevel == 1:
        if parent.size=="BTN":
            unit.callsign = f"{parent.callsign}-{nato_alphabet[num-1]}"
        else:
            unit.callsign = f"{nato_alphabet[num-1]}"
    elif unit.orglevel == 2:
        #unit.callsign = f"{grandparent.callsign}-{parent.num}-{num}"
        unit.callsign = f"{parent.callsign}-{num}"
    elif unit.orglevel >= 2:
        unit.callsign = f"{parent.callsign}-{num}"

    #if unit.size=="COY" or (unit.sizelevel<5 and not grandparent):
    #    cs = nato_alphabet[num-1]
    #else:
    #    cs = callsign
    #unit.set_callsign(callsign=cs, parent=parent, grandparent=grandparent)

    unit.sidc = unit.sidc.replace('S*','SF')

    tabs = "\t" * (unit.orglevel)
    print(tabs,unit.get_name())#,'\t',parent.callsign if parent else "NO_PARENT")
    n_sub = 1
    qwert = 0
    for x in (unit.tac_e_comp, unit.sup_e_comp):
        for element_type in x:
            for element_n in range(x[element_type]):
                el_template = unit_templates[element_type]

                el = addunit(el_template, n_sub, parent=unit, grandparent=parent, pos=unit.position)
                if qwert==0:
                    unit.tac_elements[el] = units[el].get_name()
                else:
                    unit.sup_elements[el] = units[el].get_name()

                n_sub+=1
        qwert+=1

    units[unit.unit_code] = unit
    return unit.unit_code

def addenemy(template, num, callsign=None, name=None, parent=None, greatgrandp=None, grandparent=None, pos=None, code=None):
    global unit_templates
    global basic_templates
    global enemy_units

    unit = ExternalFormation(faction="HOSTILE", unit_template=template, code=code )
    unit.num = num
    unit.parent = parent.unit_code if parent else None
    if name: unit.name = name

    if pos and parent:
        unit.position = vector_to_gps(parent.position, unit.spacing, random.randrange(0,360))
    elif pos:
        unit.position = pos
    if parent:
        unit.orglevel = parent.orglevel + 1
    else:
        unit.orglevel = 0
    
    """
    if unit.orglevel == 0:
        unit.callsign = callsign
    
    elif unit.orglevel == 1:
        unit.callsign = f"{parent.callsign}-{num}"
    elif unit.orglevel == 2:
        unit.callsign = f"{grandparent.callsign}-{parent.num}-{num}"
    elif unit.orglevel >= 2:
        unit.callsign = f"{parent.callsign}-{num}"
    """

    unit.sidc = unit.sidc.replace('S*','SH')

    tabs = "\t" * (unit.orglevel)
    print(tabs, unit.unit_code, unit.get_name())#,'\t',parent.callsign if parent else "NO_PARENT")
    n_sub = 1
    qwert = 0
    for x in (unit.tac_e_comp, unit.sup_e_comp):
        for element_type in x:
            for element_n in range(x[element_type]):
                el_template = unit_templates[element_type]

                if parent:
                    uplvls = parent.sizelevel - el_template["sizelevel"] 
                    if uplvls>=1:
                        unit.levels_up = uplvls

                el = addenemy(unit_templates[element_type], n_sub, parent=unit, greatgrandp=grandparent, grandparent=parent, pos=unit.position)
                unit.tac_elements[el] = enemy_units[el].get_name()
                n_sub+=1
        qwert += 1

    enemy_units[unit.unit_code] = unit
    return unit.unit_code


def set_coy_sub_pos(ucode, pos):
    global units
    units[ucode].position = pos
    sub_p = units[ucode].tac_elements
    for p in sub_p:
        print(p)

with open("scenario2.json","r") as file:
    scenario = json.loads(file.read())

pos_u = [
    {'lat': 36.530310, 'lon': -83.21722, 'alt': 0.0},
    {'lat': 36.530310, 'lon': -83.21722, 'alt': 0.0},
    {'lat': 36.530310, 'lon': -83.21722, 'alt': 0.0}
]

ADD_TO_DB = True

for f in scenario["forces"]:  
    fu = scenario["forces"][f]
    template = fu["category"]+"_"+fu["size"]
    pos = GPSposition(fu["pos"]["lat"], fu["pos"]["lon"],fu["pos"]["alt"])
    panther_code = addunit(unit_templates[template], 1, callsign=fu["callsign"], pos=pos, code=f)

for uc in units:
    u = units[uc]
    if u.sizelevel>=5:
        print(uc, u.get_name(), u.position.mgrs())
    if ADD_TO_DB: client.insert("units", u.as_dict())

print('\n')
print("Adding enemy")
"""
en = 1
for ec in scenario["intel_report"]["enemy"]:   
    eu = scenario["intel_report"]["enemy"][ec]
    template = eu["category"]+"_"+eu["size"]
    #cs = f"H_{eu['num']}_{eu['category']}_{eu['size']}"
    pos = GPSposition(eu["pos"]["lat"], eu["pos"]["lon"],eu["pos"]["alt"])
    eu_code = addenemy(unit_templates[template], eu['num'], name=eu["name"], pos=pos, code=ec)
    en+=1

for uc in enemy_units:
    u = enemy_units[uc]
    if u.sizelevel>=5:
        print(uc, u.get_name(), u.position.mgrs())
    if ADD_TO_DB: client.insert("intel", u.as_dict())



# Insert a new unit
print(client.insert("units", panther.as_dict()))

#new_unit = {
    "name": "X Battalion",
    "unit_code": "12345678",
    "domain": 0
}
print(client.insert("units", new_unit))

# Retrieve all units
print(client.get_all("units"))

# Retrieve specific unit by code
print(client.get("units", "unit_code", panther.unit_code))

# Update a unit
updated_fields = {"status": "Active"}
print(client.update("units", "unit_code", "12345678", updated_fields))

# Delete a unit
print(client.delete("units", "unit_code", "12345678"))


for c in tac_elements:
    n+=1
    nc+=1
    cu = CabalUnit()
    cu.unit_code = ucodes.pop()
    cu.num = nc
    c_template = tac_elements[c] 
    for i in c_template:
        setattr(cu, i, c_template[i])
    cu.parent = panther.unit_code
    cu.callsign = c#cu.callsign.replace("<coy_callsign>",c)
    cu.position = pos_u.pop(0)
    print("\t",cu.get_name())

    np = 0
    for p in cu.tac_e_comp:
        for c_e_i in range(cu.tac_e_comp[p]):
            n+=1
            np+=1
            pu = CabalUnit()
            pu.unit_code = ucodes.pop()
            pu.num = np
            p_template = unit_templates[p]
            for i in p_template:
                setattr(pu, i, p_template[i])
            pu.parent = cu.unit_code
            pu.set_callsign(parent=cu,grandparent=panther)
            pu.position = vector_to_gps(cu.position, pu.spacing, random.randrange(0,360))
            print("\t\t",pu.get_name())

            ns=0
            for s in pu.tac_e_comp:
                for p_e_i in range(pu.tac_e_comp[s]):
                    n+=1
                    ns+=1
                    su = CabalUnit()
                    su.unit_code = ucodes.pop()
                    su.num = ns
                    s_template = unit_templates[s]
                    for i in s_template:
                        setattr(su, i, s_template[i])
                    su.parent = pu.unit_code
                    su.set_callsign(parent=pu, grandparent=cu)
                    su.position = vector_to_gps(pu.position, su.spacing, random.randrange(0,360))

                    units[su.unit_code] = su
                    pu.tac_elements[su.unit_code] = su.get_name()
                    print("\t\t\t",su.get_name())

            cu.tac_elements[pu.unit_code] = pu.get_name()
            units[pu.unit_code] = pu

    
    units[cu.unit_code] = cu
    panther.tac_elements[cu.unit_code] = cu.get_name()


"""

if __name__ == "__main__":
    print("TODO")
