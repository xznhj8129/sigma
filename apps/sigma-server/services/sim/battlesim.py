import json
import copy
import string
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sigmac3_sdk.core.c2 import *
from sigmac3_sdk.core.schema import TaskStatus
from sigmac3_sdk.geo import *

DEFAULT_SPEED_KMH = 40.0
ARRIVAL_RADIUS_M = 5.0
TASK_POLL_INTERVAL = 1.0
DB_UPDATE_INTERVAL = 1.0
DT = 0.1

client = DBClient(base_url="http://localhost:5001/api")

units = {}
enemy = {}

# Retrieve all units
units_r = client.get_all("units")
for u in units_r:
    code = u["unit_code"]
    units[code] = CabalUnit()
    units[code].from_json(u)

enemy_r = client.get_all("intel")
for u in enemy_r:
    code = u["unit_code"]
    enemy[code] = ExternalFormation()
    enemy[code].from_json(u)

print('#### UNITS ####')
for i in units:
    print(i, units[i].get_name())
    for j in units[i].tac_elements:
        print('\t',j, units[i].tac_elements[j])

print()
print('#### ENEMY ####')
for i in enemy:
    print(i, enemy[i].get_name())
    for j in enemy[i].tac_elements:
        print('\t',j, enemy[i].tac_elements[j])

units_movement = {code: {"speed_kmh": DEFAULT_SPEED_KMH, "azimuth": 0.0} for code in units}
active_tasks = {}
unit_current_task = {}
db_updates = {}
last_task_poll = 0.0
last_db_update = 0.0
t = 0.0

# TODO: Create container Unit class that holds CabalUnit, created for each active unit entity and updates it's own state, applying movement, task status, current tasks and all necessary information. Updated every cyclle with unit.update()

def move_unit(unit_code):
    mv = units_movement[unit_code]
    v = (mv["speed_kmh"] / 3.6) * DT
    newpos = vector_to_gps(units[unit_code].position, v, units_movement[unit_code]["azimuth"])
    units[unit_code].position = newpos
    db_updates[unit_code] = {"position": newpos.json()}

while True:
    now = time.time()

    if now - last_task_poll >= TASK_POLL_INTERVAL:
        tasks_payload = client.get_all("tasks")
        active_tasks = {}
        unit_current_task = {}
        for task in tasks_payload:
            if task.get("task_type") not in ("move", "attack", "isr"):
                continue
            status = task.get("status")
            if status is None:
                raise RuntimeError(f"Task {task.get('task_id')} missing status")
            if status == TaskStatus.COMPLETE.value:
                continue
            active_tasks[task["task_id"]] = task
            if status == TaskStatus.NEW.value:
                client.update("tasks", "task_id", task["task_id"], {"status": TaskStatus.ACCEPTED.value, "last_update": now})
                status = TaskStatus.ACCEPTED.value
                task["status"] = status
            unit_current_task[task["unit_code"]] = task["task_id"]
        last_task_poll = now

    for unit_code, task_id in list(unit_current_task.items()):
        task = active_tasks.get(task_id)
        if task is None:
            continue

        destination = task["destination"]
        dest_pos = GPSposition(destination["lat"], destination["lon"], destination.get("alt", 0))
        vec = gps_to_vector(units[unit_code].position, dest_pos)

        if vec.dist <= ARRIVAL_RADIUS_M:
            client.update("tasks", "task_id", task_id, {"status": TaskStatus.COMPLETE.value, "last_update": now})
            task["status"] = TaskStatus.COMPLETE.value
            active_tasks.pop(task_id, None)
            unit_current_task.pop(unit_code, None)
            units_movement.pop(unit_code, None)
            continue

        if task["status"] != TaskStatus.ACTIVE.value:
            client.update("tasks", "task_id", task_id, {"status": TaskStatus.ACTIVE.value, "last_update": now})
            task["status"] = TaskStatus.ACTIVE.value

        if "speed_ms" in task and task["speed_ms"] is not None:
            speed_kmh = float(task["speed_ms"]) * 3.6
        else:
            speed_kmh = units_movement.get(unit_code, {}).get("speed_kmh", DEFAULT_SPEED_KMH)

        units_movement[unit_code] = {"speed_kmh": speed_kmh, "azimuth": vec.az}
        move_unit(unit_code)

    if now - last_db_update >= DB_UPDATE_INTERVAL and db_updates:
        for dbu, payload in db_updates.items():
            print(client.update("units", "unit_code", dbu, payload))
        db_updates.clear()
        last_db_update = now

    time.sleep(DT)
    t += DT