import copy
import time
import uuid

import numpy as np
import pandas as pd
from flask import jsonify

from sigmac3_sdk.clients.db import DBClient
from sigmac3_sdk.core.units import *
from sigmac3_sdk.core.planning import *  # noqa: F403,F401
from sigmac3_sdk.core.schema import TemplateLibrary, UNIT_CATEGORY_NAMES, UNIT_SIZE_LABELS
from sigmac3_sdk.geo import *  # noqa: F403,F401

CATEGORY_LABELS = {k.value: v for k, v in UNIT_CATEGORY_NAMES.items()}
SIZE_LABELS = {k.value: v for k, v in UNIT_SIZE_LABELS.items()}
TEMPLATE_LIB = TemplateLibrary()


def zulu_time():
    return float(time.time())

def local_time():
    return float(time.mktime(time.localtime()))

def time_sec(days=0, hours=0, minutes=0, seconds=0):
    return (days * 86400) + (hours * 3600) + (minutes * 60) + seconds

def ztime_to_str(time_int, fmt):
    return time.strftime(fmt, time.gmtime(time_int))

def localtime_to_str(time_int, fmt):
    return time.strftime(fmt, time.localtime(time_int))

def time_dhms(total_seconds):
    days = total_seconds // 86400
    remaining_seconds = total_seconds % 86400
    hours = remaining_seconds // 3600
    remaining_seconds %= 3600
    minutes = remaining_seconds // 60
    seconds = round(remaining_seconds % 60, 3)
    return days, hours, minutes, seconds




class spatial_feature():
    def __init__(self):
        self.name = ""
        self.unit_code = randcode(8)
        self.uid = str(uuid.uuid4())
        self.domain = 0 # Ground, Air, Sea, Underwater
        self.status = 0 # Present, Damaged, Xdestroyed, Lost, Decoy/fake
        self.category = "" # object, topography, landmark, polygon
        self.type = "" # bridge, building, base, etc
        self.name = ""
        self.cot = ""
        self.sidc = ""
        self.status = ""
        self.position = GPSposition(0,0,0)
        self.polygon_shape = ""
        self.polygon = []


def load_db(client):
    units_r = client.get_all("units")
    for u in units_r:
        code = u["unit_code"]
        units[code] = CabalUnit()
        units[code].from_json(u)
        
    enemy_r = client.get_all("units")
    for u in units_r:
        code = u["unit_code"]
        enemy[code] = CabalUnit()
        enemy[code].from_json(u)
    return units, enemy


def get_orbat(units, ucode, depth=0, verbose=False):
    u = units[ucode]
    if verbose: print('\t'*depth, u.num, u.category, u.size, u.callsign, u.unit_code)
    orbat = {
        "personnel":0,
        "infantry":0,
        "vehicles":{},
        "weapons":{},
        "air_units":{},
    }
#        "equipment": {},
#        "ammo": {},
#    }

    if hasattr(u,"personnel"):
        orbat["personnel"]+= u.personnel
    if hasattr(u,"infantry"):
        orbat["infantry"] += u.infantry
    if hasattr(u,"vehicles"):
        for veh in u.vehicles:
            if veh not in orbat["vehicles"]: orbat["vehicles"][veh] = 0
            orbat["vehicles"][veh] += u.vehicles[veh]
    if hasattr(u,"weapons"):
        for veh in u.weapons:
            if veh not in orbat["weapons"]: orbat["weapons"][veh] = 0
            orbat["weapons"][veh] += u.weapons[veh]
    if hasattr(u,"air_units"):
        for veh in u.air_units:
            if veh not in orbat["air_units"]: orbat["air_units"][veh] = 0
            orbat["air_units"][veh] += u.air_units[veh]
        
    #print('\t'*depth,orbat)

    for el in (u.tac_elements, u.sup_elements):
        for i in el:
            e = units[i]
            forces = get_orbat(units, i, depth=depth+1)
            orbat["personnel"]+= forces["personnel"]
            orbat["infantry"] += forces["infantry"]

            for veh in forces["vehicles"]:
                if veh not in orbat["vehicles"]: orbat["vehicles"][veh] = 0
                orbat["vehicles"][veh] += forces["vehicles"][veh]

            for veh in forces["weapons"]:
                if veh not in orbat["weapons"]: orbat["weapons"][veh] = 0
                orbat["weapons"][veh] += forces["weapons"][veh]

            for veh in forces["air_units"]:
                if veh not in orbat["air_units"]: orbat["air_units"][veh] = 0
                orbat["air_units"][veh] += forces["air_units"][veh]

    #print('\t'*depth,orbat)
    return orbat

def get_uav_orbat(units, ucode, depth=0, verbose=False):
    u = units[ucode]
    #if verbose:
    #print('\t### '*depth, u.num, u.category, u.size, u.callsign, u.unit_code)
    orbat = {
        "links": {},
        "air_units":{}, #ammo, etc
    }

    for veh in u.air_units:
        if veh not in orbat["air_units"]: orbat["air_units"][veh] = 0
        orbat["air_units"][veh] += u.air_units[veh]

    if len(u.links)>0:
        orbat["links"] = u.links
        
    #print('\t'*depth,orbat)

    for el in (u.tac_elements, u.sup_elements):
        for i in el:
            e = units[i]
            forces = get_uav_orbat(units, i, depth=depth+1)
            for veh in forces["air_units"]:
                if veh not in orbat["air_units"]: orbat["air_units"][veh] = 0
                orbat["air_units"][veh] += forces["air_units"][veh]

            for veh in forces["links"]:
                if veh not in orbat["links"]: orbat["links"][veh] = 0
                orbat["links"][veh] += forces["links"][veh]
                #orbat["links"][i] = e.links

    """for veh in u.air_units:
        if veh not in orbat[ucode]["air_units"]: orbat[ucode]["air_units"][veh] = 0
        orbat[ucode]["air_units"][veh] += u.air_units[veh]

    if len(u.links)>0:
        orbat[ucode]["links"] = u.links
        
    #print('\t'*depth,orbat)

    for el in (u.tac_elements, u.sup_elements):
        for i in el:
            e = units[i]
            forces = get_uav_orbat(units, i, depth=depth+1)
            for ucode2 in forces:
                if ucode2 not in orbat:
                    orbat[ucode2] = {
                        "air_units": {},
                        "links": {}
                    }
                for veh in forces[ucode2]["air_units"]:
                    if veh not in orbat[ucode2]["air_units"]: orbat[ucode2]["air_units"][veh] = 0
                    orbat[ucode2]["air_units"][veh] += forces[ucode2]["air_units"][veh]
                    orbat[ucode2]["links"][i] = e.links
                    """

    #print('\t'*depth, orbat)
    return orbat


def format_text_uav_assets(units, unit):
    ucode = unit.unit_code
    airs = {}
    callcodes = {}
    orbat = get_orbat(units, ucode)
    for x in (unit.tac_elements, unit.sup_elements):
        for e in x:
            a_orbat = None
            eu = units[e]
            e_orbat = get_orbat(units, e)
            callcodes[eu.callsign] = e
            if 'air_units' in e_orbat:
                a_orbat = get_uav_orbat(units, e)
            airs[eu.callsign] = a_orbat
            
    uavinfo = {}
    air_txt = ""
    if len(airs)>0:
        ak = list(airs.keys())
        ak.sort()
        for i in ak:
            au = units[callcodes[i]]
            drones = airs[i]["air_units"]
            links = airs[i]["links"]
            
            if len(drones)>0: air_txt+=f"{i} UAV capabilities:\n"
            simult = {}
            for model in drones:
                n = drones[model]
                dronemodel = TEMPLATE_LIB.air_units[model].model_dump()
                simult_rc = links.get(dronemodel["rc_link"], 0)
                simult[model] = simult_rc
                air_txt+=f"\tcan control {simult_rc}x {model} simultaneously\n"
                frt = "(Mission Radius)" if dronemodel["reusable"] else "(One way)"
                uavinfo[model] = f"""{model} info: 
    Attack modes: {dronemodel["attack_modes"]}, 
    Max speed: {dronemodel["max_spd"]}km/h, 
    Max range: {dronemodel["max_range"]/1000}km {frt}, 
    Max flight time: {round(dronemodel["max_flight_t"]/60.0)}min"""

            if len(drones)>0: air_txt+='\n'
    for i in uavinfo:
        air_txt+=f'{uavinfo[i]}\n'
    return air_txt

def format_text_uav_capability(model):   
    uavinfo = {}
    air_txt = ""

    dronemodel = TEMPLATE_LIB.air_units[model].model_dump()
    frt = "(Mission Radius)" if dronemodel["reusable"] else "(One way)"
    uavinfo[model] = f"""{model} info: 
Attack modes: {dronemodel["attack_modes"]}, 
Max speed: {dronemodel["max_spd"]}km/h, 
Max range: {dronemodel["max_range"]/1000}km {frt}, 
Max flight time: {round(dronemodel["max_flight_t"]/60.0)}min"""

    for i in uavinfo:
        air_txt+=f'{uavinfo[i]}\n'
    return air_txt


def format_text_orbat(units, unit):
    ucode = unit.unit_code
    callcodes = {}
    airs = {}
    orbat = get_orbat(units, ucode)
    tac_e = {}
    sup_e = {}
    eee=0
    for x in (unit.tac_elements, unit.sup_elements):
        for e in x:
            a_orbat = None
            eu = units[e]
            e_orbat = get_orbat(units, e)
            callcodes[eu.callsign] = e
            txt = f"{eu.callsign} ({eu.num} {CATEGORY_LABELS[eu.category]} {SIZE_LABELS[eu.size]}) {e_orbat}\n"

            if eee==0:
                tac_e[eu.callsign] = txt
            else:
                sup_e[eu.callsign] = txt
        eee+=1
    
    tac_e_txt = ""
    ste = list(tac_e.keys())
    ste.sort()
    for i in ste:
        tac_e_txt+=tac_e[i]
    sse = list(sup_e.keys())
    sse.sort()
    sup_e_txt = ""
    for i in sse:
        sup_e_txt+=sup_e[i]

    msg_v = {}
    fs = list(tac_e.keys()) + list(sup_e.keys())
    fs.sort()
    for i in fs:
        msg_v[i] = "<one string containing the task orders>"

    return {
        "json_tasks_val": msg_v,
        "tac_e": tac_e,
        "sup_e": sup_e,
        "tac_e_txt": tac_e_txt,
        "sup_e_txt": sup_e_txt
    }

def format_text_timeline(scenario):
    tl_type = scenario["timetable"]["type"]
    if tl_type == "immediate":
        starttime = local_time()
        timeline = f'Carry out immediately.\n'
    else:
        starttime = scenario["timetable"]["start"]

        start_str = localtime_to_str(starttime, "%d/%m/%Y %H%M Hours")
        timeline = f'Begin operation: {start_str}\n'
        t = starttime

        if tl_type == "phased":
            #time_sec(days=0, hours=12, minutes=0, seconds=0)
            for pt in scenario["timetable"]["phases"]:
                phase = scenario["timetable"]["phases"][pt]
                th = localtime_to_str(starttime + time_sec(hours=phase["t"]["hours"]), "%H%M")
                h = localtime_to_str(starttime + time_sec(hours=phase["t"]["hours"]), "%d/%m/%y %H%M")
                timeline+= f'T+{phase["t"]["hours"]}H ({h} Hours): {phase["goal"]}'

                if phase["type"] == "from":
                    timeline+= f' by T+{phase["t"]["hours"]}H ({th} Hours) and until further notice'
                else:
                    timeline+= f' {phase["type"]} T+{phase["t"]["hours"]}H ({th} Hours)'

                timeline+= f'\n'

    return timeline

def spatial_view(unit, units, enemy={}, topo_features={}, maxdist=0):
    view = ''
    vf = {}
    vh = {}
    vt = {}
    
    # Skip comparing the unit with itself
    for u in units:
        if units[u].callsign != unit.callsign and units[u].position.json() != unit.position.json():
            #print(unit.position, units[u].position)
            v = gps_to_vector(unit.position, units[u].position)
            if maxdist <= 0 or (maxdist > 0 and v.dist <= maxdist):
                vf[units[u].callsign] = v

    for u in enemy:
        if enemy[u].position.json() != unit.position.json():
            v = gps_to_vector(unit.position, enemy[u].position)
            if maxdist <= 0 or (maxdist > 0 and v.dist <= maxdist):
                vh[enemy[u].unit_code] = v

    for u in topo_features:
        if topo_features[u].position.json() != unit.position.json():
            v = gps_to_vector(unit.position, topo_features[u].position)
            if maxdist <= 0 or (maxdist > 0 and v.dist <= maxdist):
                vt[topo_features[u].unit_code] = v
    
    return {
        "friendly": vf,
        "hostile": vh,
        "feature": vt
    }


def find_closest_units(reference_unit, units_dict, n=1):
    """
    Finds the n closest units to a reference unit using geodesic distance (in meters).

    Args:
        reference_unit: The reference unit object.
        units_dict: A dictionary of unit objects.
        n: The number of closest units to return.

    Returns:
        list: A list of DataFrames, each containing details of one of the n closest units.
    """
    # Get reference unit's position
    ref_lat = reference_unit.position.lat
    ref_lon = reference_unit.position.lon

    # Calculate distances using geodesic distance (meters)
    distances = []
    for unit_code, unit in units_dict.items():
        dist_m = gps_distance_m(reference_unit.position, unit.position)
        distances.append({
            'unit_code': unit_code,
            'unit_name': unit.get_name(),
            'distance': dist_m
        })

    # Sort by distance and select top n
    sorted_distances = sorted(distances, key=lambda x: x['distance'])[:n]

    # Convert to a list of DataFrames
    result_list = [
        pd.DataFrame({
            'unit_code': [d['unit_code']],
            'unit_name': [d['unit_name']],
            'distance': [d['distance']]
        }) for d in sorted_distances
    ]

    return result_list


def get_centroid(units):
    n = float(len(units))
    slat = sum(u.position.lat for u in units)
    slon = sum(u.position.lon for u in units)
    salt = sum(u.position.alt for u in units)
    return GPSposition(slat / n, slon / n, salt / n)
