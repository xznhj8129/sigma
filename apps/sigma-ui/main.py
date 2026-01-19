import asyncio
from aiohttp import web
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask import send_from_directory, abort
import json
import random
import os  
import math
import uuid
import time
import re
import requests
import sys
import logging
from pathlib import Path
from dataclasses import dataclass
import io

import configparser
from tinydb import TinyDB, Query
from time import localtime, strftime
from threading import Thread, Lock

REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / "sdk" / "sigmac3-sdk"
if SDK_PATH.exists():
    sys.path.insert(0, str(SDK_PATH))

from sigmac3_sdk.geo import *
from sigmac3_sdk.core.c2 import *
from sigmac3_sdk.core.schema import TASK_SCHEMAS, TaskKind, TaskStatus
from pydantic import ValidationError
import uuid as _uuid


from webrtc_server import create_aiohttp_app  
from ws_stream import StreamHub, attach_stream_routes
from werkzeug.exceptions import HTTPException

from modules.planning import *
from modules.observers import *
from modules.ataklib import start_atak_service

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT.parent.parent / "configs" / "sigma-ui.sample.ini"
SOURCES_PATH = ROOT / "sources.json"
aio_thread: Thread | None = None
ws_started = False
ws_failed = False
_ws_state_lock = Lock()

def ensure_db_client():
    global client, stream_hub, ws_started, ws_failed
    if client is not None:
        return client
    try:
        client = DBClient(base_url=f"http://{cfg_c3db_server}:{cfg_c3db_port}/api")
        client.get_all("units")
        if stream_hub is None:
            stream_hub = StreamHub(client)
        with _ws_state_lock:
            ws_started = False
            ws_failed = False
        return client
    except Exception as exc:
        client = None
        raise RuntimeError(f"C3 database client not available: {exc}")


@app.errorhandler(HTTPException)
def _json_http_error(exc: HTTPException):
    payload = {"error": exc.name, "description": exc.description}
    resp = exc.get_response()
    resp.data = json.dumps(payload)
    resp.content_type = "application/json"
    return resp


@app.errorhandler(Exception)
def _json_unhandled_error(exc: Exception):
    logging.exception("Unhandled server error")
    return jsonify({"error": "Internal Server Error", "description": str(exc)}), 500
_ws_state_lock = Lock()

class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            s.write(data)
        return len(data)
    def flush(self):
        for s in self.streams:
            s.flush()

config = configparser.ConfigParser()
if not config.read(CONFIG_PATH):
    raise RuntimeError(f"Config missing or unreadable: {CONFIG_PATH}")

cfg_host = config.get('Connections', 'host')
cfg_port = int(config.get('Connections', 'port'))
cfg_c3db_server = config.get('Connections', 'c3db_server')
cfg_c3db_port = int(config.get('Connections', 'c3db_port'))

imagery_dir = config.get('Paths', 'imagery_dir')
data_dir = config.get('Paths', 'data_dir')
log_dir = config.get('Paths', 'log_dir')

debug = config.getboolean('Settings', 'debug')
timeout = int(config.getint('Settings', 'timeout'))

# Decoding a JSON encoded dictionary from a string
#options_str = config.get('Settings', 'options')
#options = json.loads(options_str)
# Logging to both stdout and file
log_dir_path = Path(log_dir)
if not log_dir_path.is_absolute():
    log_dir_path = (ROOT / log_dir_path).resolve()
try:
    log_dir_path.mkdir(parents=True, exist_ok=True)
except Exception as exc:
    raise RuntimeError(f"Cannot create log directory {log_dir_path}: {exc}") from exc
log_path = log_dir_path / "sigma-ui.log"
log_file = log_path.open("a", encoding="utf-8")
sys.stdout = Tee(sys.stdout, log_file)
sys.stderr = Tee(sys.stderr, log_file)
ws_log_path = log_dir_path / "sigma-ui-aiohttp.log"
# Route aiohttp/ws logs to a file as well
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler(ws_log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("aiohttp.access").propagate = True
logging.getLogger("aiohttp.server").propagate = True

print("Imagery Directory:", imagery_dir)
print("Data Directory:", data_dir)
print("Log Directory:", log_dir_path)
print("Debug Mode:", debug)
print("Timeout:", timeout)
#print("Options:", options)

ips = [ # dev examples
    convert_geopaste("geo:36.530310,-83.21722;crs=wgs84;u=0"),
    convert_geopaste("geo:36.530310,-83.21722;crs=wgs84;u=0"),
    convert_geopaste("geo:36.530310,-83.21722;crs=wgs84;u=0")    
]
try:
    client = DBClient(base_url=f"http://{cfg_c3db_server}:{cfg_c3db_port}/api")
    units = client.get_all("units")
    intel = client.get_all("intel")
except Exception as exc:
    print(f"Could not connect to DB at http://{cfg_c3db_server}:{cfg_c3db_port}/api: {exc}")
    client = None
    units = {}
    intel = {}

info_points = []
for i in ips:
    puid = str(uuid.uuid4())
    info_points.append(
        {
            "pos": i,
            "name": "test",
            "origin": "debug",
            "uid": puid,
            "cot": None,
            "SIDC": 30061000001211000000,
            "added": strftime("%d %b %Y %H:%M:%S", localtime()),
            "t_stale": -1,
            "url": f"/intel/{puid}"
        }
    )


current_mode = None
mission_type = "survey"
mission_data = gen_blankmission()
start_location = [36.530310,-83.21722]  

sysid = hex(uuid.getnode())
shapes_store: dict[str, dict] = {}


#with open("templates/basic_templates.json","r") as file:
#    basic_templates = json.loads(file.read())
#with open("templates/units.json","r") as file:
#    templ_units = json.loads(file.read())
#with open("templates/components.json","r") as file:
#    templ_components = json.loads(file.read())
#with open("templates/units.json","r") as file:
#    templ_air_units = json.loads(file.read())


##############
# Flask routes
##############

@app.route("/")
def index():
    return render_template("workspace.html")

@app.route("/map")
def map_tile():
    return render_template("map.html")
    
@app.route("/map2")
def map2_tile():
    return render_template("map2.html")

@app.route("/image")
def image_tile():
    return render_template("image.html")

@app.route("/test")
def test_tile():
    return render_template("test.html")

@app.route("/video")
def video_tile():
    return render_template("video.html")

@app.route("/chat")
def chat_tile():
    return render_template("chat.html")


###################
# Imagery viewer
###################
with SOURCES_PATH.open("r", encoding="utf-8") as f:
    obs_sources = json.load(f)
FILE_ROOT = Path(obs_sources["files"]["path"]).resolve()

IMAGERY_DIR = FILE_ROOT
IMAGE_DIR = os.path.join(IMAGERY_DIR, "image")
VIDEO_DIR = os.path.join(IMAGERY_DIR, "video")
Path(IMAGE_DIR).mkdir(parents=True, exist_ok=True)
Path(VIDEO_DIR).mkdir(parents=True, exist_ok=True)

def list_media_files():
    with SOURCES_PATH.open("r", encoding="utf-8") as f:
        obs_sources = json.load(f)
    image_files = os.listdir(IMAGE_DIR) if os.path.exists(IMAGE_DIR) else []
    video_files = os.listdir(VIDEO_DIR) if os.path.exists(VIDEO_DIR) else []
    return image_files, video_files


@app.route('/imagery_map')
def imagery_map():
    global start_location
    zoom_level = 13
    return render_template('imagery_map.html', location=start_location, zoom=zoom_level)

@app.route("/api/imagery/list")
def imagery_list():
    images, videos = list_media_files()
    all_entries = images + videos + [k for k in obs_sources if k != "files"]
    for i in all_entries:
        print(i)
    return jsonify(sorted(all_entries))

@app.route("/api/imagery/path/<name>")
def imagery_metadata(name):
    images, videos = list_media_files()
    
    if name in images:
        filepath = f"/api/imagery/file/image/{name}"
        metadata = import_photo(os.path.join(IMAGE_DIR, name))
        return jsonify({
            "type": "photo",
            "latlon":[metadata.pos["lat"],metadata.pos["lon"]],
            "alt":metadata.pos["alt"],
            "fov":metadata.fov,
            "path": filepath
        })

    if name in videos:
        return jsonify({
            "type": "webrtc",
            "path": name  # logical name used by webrtc_server
        })

    if name in obs_sources:
        return jsonify({
            "type": obs_sources[name].get("video_type", "webrtc"),
            "path": name
        })

    abort(404)

@app.route("/api/imagery/file/<folder>/<filename>")
def serve_image_file(folder, filename):
    if folder not in ["image"]:  # only allow direct serving of static images
        abort(403)
    safe_path = os.path.join(IMAGERY_DIR, folder, filename)
    if not os.path.isfile(safe_path):
        abort(404)
    return send_from_directory(os.path.join(IMAGERY_DIR, folder), filename)


@app.route('/api/mark', methods=['POST'])
def handle_click():
    data = request.get_json()
    print(data)
    return jsonify({"status": "success"}), 200

###################
# UAV Mission Planning
###################
@app.route('/planner')
def planner():
    global mission_data, start_location
    zoom_level = 13
    return render_template('planner_map.html', location=start_location, zoom=zoom_level, uid=mission_data["mission_uid"])

@app.route('/planner/result')
def planner_result():
    global mission_data
    plan = render_opplan(mission_data)
    head_match = re.search(r'<head>(.*?)</head>', plan, re.DOTALL)
    body_match = re.search(r'<body>(.*?)</body>', plan, re.DOTALL)
    scripts_match = re.search(r'</body>(.*?)</html>', plan, re.DOTALL)

    map_head = head_match.group(1) if head_match else ''
    map_body = body_match.group(1) if body_match else ''
    map_scripts = scripts_match.group(1) if scripts_match else ''

    return render_template('waypoints_map.html', map_head=map_head, map_body=map_body, map_scripts=map_scripts)

# Flask endpoint for adding a GPS point
@app.route('/api/planner/add_point', methods=['POST'])
def planner_add_point():
    global mission_data, current_mode, mission_type

    data = request.json
    print("add_point",current_mode, data)
    if current_mode:
        if current_mode == "route_in" or current_mode == "route_out":
            point_type = "waypoint"
        else:
            point_type = current_mode

        if current_mode in ("home", "land"):
            n = 0
        else:
            n = mission_data["n_points"][current_mode]
            mission_data["n_points"][current_mode]+=1

        point = {
            "num": n,
            "point_type": point_type,
            "category": current_mode,
            "pos": GPSposition(data['lat'], data['lon'], 0)
        }

        print("point",point)
        if point_type == "home":
            mission_data["home_pos"] = point['pos']
        elif point_type == "land":
            mission_data["land_pos"] = point['pos']
        else:
            mission_data["points"][current_mode].append(point)

        #mission_type = data["missiontype"]
        mission_data["mission_type"] = mission_type
        mission_data["route_in"] = mission_data["points"]["route_in"]
        mission_data["survey"] = mission_data["points"]["survey"]
        mission_data["route_out"] = mission_data["points"]["route_out"]
        return jsonify(success=True)
    else:
        return jsonify(success=False)

@app.route('/api/planner/add_shape', methods=['POST'])
def planner_add_shape():
    global mission_data, current_mode, mission_type

    data = request.json
    print("add_shape",data)
    if current_mode:
        point_type = current_mode

        n = mission_data["n_points"][current_mode]
        mission_data["n_points"][current_mode]+=1

        point = {
            "num": n,
            "point_type": point_type,
            "category": current_mode,
            "zone": data
        }

        print("shape",point)
        if point_type == "home":
            mission_data["home_pos"] = point['pos']
        elif point_type == "land":
            mission_data["land_pos"] = point['pos']
        else:
            mission_data["points"][current_mode].append(point)

        #mission_type = data["missiontype"]
        mission_data["mission_type"] = mission_type
        mission_data["route_in"] = mission_data["points"]["route_in"]
        mission_data["survey"] = mission_data["points"]["survey"]
        mission_data["route_out"] = mission_data["points"]["route_out"]
        return jsonify(success=True)

    else:
        return jsonify(success=False)

@app.route('/api/planner/set_mode', methods=['POST'])
def planner_set_mode():
    global mission_data, current_mode, mission_type
    data = request.json
    current_mode = data['mode'].replace('-','_')
    mission_type = data["type"]
    mission_data["mission_type"] = mission_type
    print('set_mode:', current_mode, mission_type)
    return jsonify(success=True)

@app.route('/api/planner/map_data', methods=['GET'])
def planner_map_data():
    global mission_data, current_mode, info_points
    jsonips = []
    for i in info_points:
        j = i.copy()
        j["pos"] = i["pos"].latlon()
        jsonips.append(j)

    data = {
        "uid": mission_data["mission_uid"],
        "home_pos": mission_data["home_pos"].latlon() if mission_data["home_pos"] else None ,
        "route_in": [i['pos'].latlon() for i in mission_data["points"]["route_in"]],
        "survey": [i['pos'].latlon() for i in mission_data["points"]["survey"]],
        "route_out": [i['pos'].latlon() for i in mission_data["points"]["route_out"]],
        "land_pos": mission_data["land_pos"].latlon() if mission_data["land_pos"] else None,
        "info_points": jsonips,
    }
    return jsonify(data)

@app.route('/api/planner/undo_last', methods=['POST'])
def planner_undo_last():
    global mission_data, current_mode
    if current_mode not in (None, "home", "land"):
        if len(mission_data["points"][current_mode])>0:
            mission_data["points"][current_mode].pop()
            mission_data["n_points"][current_mode]-=1
            mission_data["route_in"] = mission_data["points"]["route_in"]
            mission_data["survey"] = mission_data["points"]["survey"]
            mission_data["route_out"] = mission_data["points"]["route_out"]
    return jsonify(success=True)

@app.route('/api/planner/clear_all', methods=['POST'])
def planner_clear_all():
    global mission_data, current_mode
    mission_data = gen_blankmission()
    current_mode = None
    return jsonify(success=True)


@app.route('/api/planner/gen_plan', methods=['POST'])
def planner_gen_plan():
    global mission_data, current_mode
    if len(mission_data["survey"])>0 and len(mission_data["points"]["route_in"])>0 and len(mission_data["points"]["route_out"])>0:
        mission_data = plan_mission(mission_data)
        return redirect(url_for('result'))
    else:
        return jsonify(success=False,err="Incomplete plan")


@app.route('/api/planner/save', methods=['POST'])
def planner_save():
    global mission_data, current_mode

    data = request.get_json()
    polygons = data.get('polygons', [])
    rectangles = data.get('rectangles', [])
    circles = data.get('circles', [])
    print(polygons)
    print(rectangles)
    print(circles)
    print(mission_data)
    with open("mission.plan", "w") as f: 
        f.write(json.dumps(mission_data, default=lambda obj: obj.json() if isinstance(obj, GPSposition) else None))

    return jsonify(success=True)

#############
# Markers
#############

@app.route('/api/map/units')
def get_units():
    try:
        ensure_db_client()
    except Exception as exc:
        abort(500, description=str(exc))

    try:
        live_units = client.get_all("units")
    except Exception as exc:
        abort(500, description=f"Failed to fetch units: {exc}")

    units_data = []
    for u in live_units:
        unit = CabalUnit()
        unit.from_json(u)
        units_data.append([
            [unit.position.lat, unit.position.lon],
            unit.sidc,
            unit.callsign,
            unit.get_name(),
            unit.unit_code
        ])
    return jsonify(units_data)

@app.route('/api/map/tak')
def get_tak():
    try:
        ensure_db_client()
    except Exception as exc:
        abort(500, description=str(exc))

    try:
        cot_markers = client.get_all("tak")
    except Exception as exc:
        abort(500, description=f"Failed to fetch tak markers: {exc}")

    markers = []
    for m in cot_markers:
        point = m.get("point")
        if not point or "lat" not in point or "lon" not in point:
            abort(500, description=f"Missing point for tak marker: {m}")
        markers.append({
            "uid": m.get("uid"),
            "cot": m.get("cot"),
            "sidc": m.get("sidc"),
            "callsign": m.get("callsign"),
            "affiliation": m.get("affiliation"),
            "lat": float(point["lat"]),
            "lon": float(point["lon"]),
            "alt": point.get("alt"),
            "how": m.get("how"),
            "time": m.get("time"),
            "start": m.get("start"),
            "stale": m.get("stale"),
            "detail": m.get("detail"),
            "raw": m.get("raw"),
        })
    return jsonify(markers)

@app.route('/api/map/markers', methods=['GET'])
def map_data():
    global info_points
    jsonips = []
    for i in info_points:
        j = i.copy()
        j["pos"] = i["pos"].latlon()
        jsonips.append(j)

    data = {
        "info_points": jsonips,
        "shapes": list(shapes_store.values()),
    }
    return jsonify(data)

@app.route('/api/map/shapes', methods=['GET'])
def map_shapes():
    return jsonify(list(shapes_store.values()))

# Flask endpoint for adding a GPS point
@app.route('/api/map/add_point', methods=['POST'])
def map_add_point():
    data = request.json
    print("add_point", data)
    return jsonify(success=True)

@app.route('/api/map/add_shape', methods=['POST'])
def map_add_shape():
    data = request.json or {}
    shape_id = str(_uuid.uuid4())
    feature = data.copy()
    feature["id"] = shape_id
    shapes_store[shape_id] = feature
    return jsonify(feature)


@app.route('/api/map/update_shape/<shape_id>', methods=['PUT'])
def map_update_shape(shape_id):
    data = request.json or {}
    if shape_id not in shapes_store:
        abort(404, description="Shape not found")
    data["id"] = shape_id
    shapes_store[shape_id] = data
    return jsonify(data)


@app.route('/api/map/delete_shape/<shape_id>', methods=['DELETE'])
def map_delete_shape(shape_id):
    if shape_id in shapes_store:
        shapes_store.pop(shape_id)
        return jsonify({"deleted": shape_id})
    abort(404, description="Shape not found")


@app.route('/api/map/tasks/<unit_code>')
def map_unit_tasks(unit_code):
    try:
        ensure_db_client()
    except Exception as exc:
        abort(500, description=str(exc))
    try:
        tasks = client.get("tasks", "unit_code", unit_code)
    except Exception as exc:
        abort(500, description=f"Failed to fetch tasks: {exc}")
    return jsonify(tasks)


@app.route('/api/map/tasks', methods=['POST'])
def map_create_task():
    if client is None:
        abort(500, description="C3 database client not available")

    payload = request.get_json(silent=True)
    if not payload:
        abort(400, description="No task payload provided")

    try:
        task_kind = payload.get("task_type")
        if not task_kind:
            abort(400, description="task_type is required")
        schema_cls = TASK_SCHEMAS.get(TaskKind(task_kind))
        if not schema_cls:
            abort(400, description=f"Unsupported task_type {task_kind}")
        task = schema_cls(**payload)
    except ValidationError as exc:
        abort(400, description=str(exc))
    except Exception as exc:
        abort(400, description=str(exc))

    task_data = task.model_copy(update={"last_update": time.time()}).model_dump()

    try:
        client.insert("tasks", task_data)
    except Exception as exc:
        abort(500, description=f"Failed to store task: {exc}")

    return jsonify(task_data)


@app.route('/api/map/tasks_active', methods=['GET'])
def map_active_tasks():
    try:
        ensure_db_client()
    except Exception as exc:
        abort(500, description=str(exc))
    try:
        tasks = client.get_all("tasks")
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return jsonify([])
        abort(500, description=f"Failed to fetch tasks: {exc}")
    except Exception as exc:
        abort(500, description=f"Failed to fetch tasks: {exc}")
    active = [t for t in tasks if t.get("status") != TaskStatus.COMPLETE.value]
    return jsonify(active)


@app.route('/api/map/tasks/cancel/<unit_code>', methods=['POST'])
def map_cancel_tasks(unit_code):
    try:
        ensure_db_client()
    except Exception as exc:
        abort(500, description=str(exc))
    try:
        client.delete("tasks", "unit_code", unit_code)
    except Exception as exc:
        abort(500, description=f"Failed to cancel tasks: {exc}")
    return jsonify({"cancelled": unit_code})

###############
# Tests
###############
@app.route('/testmap')
def testmap():
    global start_location
    zoom_level = 13
    return render_template('map2.html', location=start_location, zoom=zoom_level)


# aiohttp app for WebRTC (built per loop inside start_aiohttp)
_aio_lock = Lock()
stream_hub = StreamHub(client) if client else None
aio_thread: Thread | None = None

def run_flask():
    app.run(
        host=cfg_host,
        port=cfg_port,
        debug=True,
        use_reloader=False  
    )

async def start_aiohttp():
    global ws_started, ws_failed
    aio_app = create_aiohttp_app()
    if stream_hub:
        attach_stream_routes(aio_app, stream_hub)
    runner = web.AppRunner(aio_app)
    await runner.setup()
    webrtcport = cfg_port+1
    try:
        site = web.TCPSite(runner, cfg_host, webrtcport)
        await site.start()
        ws_started = True
        print(f"WebRTC offer handler running at http://{cfg_host}:{webrtcport}")
    except OSError as exc:
        ws_failed = True
        print(f"WebRTC/WS sidecar failed to bind {cfg_host}:{webrtcport}: {exc}")

def _ensure_ws_sidecar():
    global aio_thread
    try:
        ensure_db_client()
    except Exception as exc:
        print(str(exc))
        return
    if stream_hub is None:
        return
    if ws_started or ws_failed:
        return
    with _aio_lock:
        if ws_started or ws_failed:
            return
        if aio_thread and aio_thread.is_alive():
            return
        def runner():
            try:
                asyncio.run(start_aiohttp())
            except Exception as exc:
                print(f"WebRTC/WS sidecar failed to start: {exc}")
        aio_thread = Thread(target=runner, daemon=True)
        print(f"Starting WS/WebRTC sidecar thread on {cfg_host}:{cfg_port+1}")
        aio_thread.start()

@app.before_request
def _start_ws_sidecar():
    _ensure_ws_sidecar()

async def process_atak_messages(in_queue: asyncio.Queue):
    while True:
        # Wait for a parsed TakMessage from the ATAK receiver
        message = await in_queue.get()
        try:
            # Assuming the message has a cotEvent field with detail.contact and lat/lon fields
            cot_event = message.cotEvent
            callsign = cot_event.detail.contact.callsign
            lat = cot_event.lat
            lon = cot_event.lon
            print(f"Received ATAK message: callsign = {callsign}, lat = {lat}, lon = {lon}")
        except Exception as e:
            print(f"Error processing ATAK message: {e}")

async def main():
    # Start Flask in a separate thread
    Thread(target=run_flask, daemon=True).start()
    print(f"Flask server running at http://{cfg_host}:{cfg_port}")

    # Start aiohttp for WebRTC
    _ensure_ws_sidecar()

    # Start the ATAK service; get inbound and outbound queues.
    atak_in_queue, atak_out_queue = await start_atak_service()

    # Start a background task to process incoming ATAK messages.
    asyncio.create_task(process_atak_messages(atak_in_queue))


    # Keep the event loop running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
