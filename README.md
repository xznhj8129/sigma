# Σ

## Sigma: Open Source C2IS (Command and Control Information System)
My own Multi-domain Command-and-Control system.

**Requirements:**
* Offline/LAN-capable client

## Browser front-end
- GoldenLayout
- WinBox

## Features
### Integrations
- ATAK/Cursor-on-Target
- ☐ ATAK integration
- ☐ XMPP integration
- ☐ Telegram integration
- ☐ Discord integration


### Situation Map
- ☐ Leaflet map with COT markers
- ☐ Live updates through ISR database and ATAK
- ☐ Shape drawing

### IMINT Interface
- ☑ Static images, recorded video, live video via WebRTC
- ☐ Scroll-zoom, Drag-pan, Click to mark
- ☐ Geopointing with metadata or telemetry
- ☐ Sync with database
- ☐ MediaMTX integration

### Chat Interface
- ☐ Multi-endpoint text chat with attachments

### Drone Control
- High level intent-based GCS
- Live control through map
- Waypoint mission planner
- Swarm control/planner

### ATAK Integration
- ☐ UDP Multicast and/or server connection
- ☐ TAK servers integration
- ☐ Live marker update
- ☐ Geochat
- ☐ Takserver/FTS/OTS compatibility
- ☐ taky (built-in?)

### Security
- TLS
- Authentification

### Settings
- C2 Server host and auth config
- TAK server host and auth config

### Connections
- 802.11s
- WebSockets
- Meshtastic
- Ham radio

### More TODO:
- multi-videos
- video relay/proxy/mediamtx program
- geopointing
- Cursor-on-target!!!

## Top-level layout
- `apps/`
  - `sigma-ui/` – Browser/front-end (Flask/AioHTTP + templates/static). Calls Sigma server API/WS only; no domain models live here.
  - `sigma-server/`
    - `api/` – REST/WS front door for UI/external clients. Validates against SDK core schemas.
    - `services/` – Long-lived/internal loops: task awareness, timekeeping/clock, sim/execution (former cncbot/battlesim), AI/OODA, observers, connectors, controllers, etc. Uses SDK core.
    - `adapters/` – Operational format translations (Hivelink, HiveOS, Mavlink, MSP, COT/ATAK, SIDC, etc) using SDK core. No transport code here.
  - `sigma-db/` – Storage service (TinyDB for now). CRUD only; no domain logic.
- `sdk/`
  - `sigmac3-sdk/`
    - `core/` – Single source of truth for schemas/templates/enums/constants and operational protocol payload builders/parsers (COT/ATAK/SIDC). Generates C4ISR schema docs.
    - `clients/` – Technical transports: REST/WS clients for server/db, WebRTC/WebSocket helpers. No C2 semantics.
    - `geo/` – Geo math utilities (from froggeolib) if kept separate from core.
- `libs/` – Optional supporting libs that are not part of the SDK surface.
- `configs/` – Per-app config/env samples (no hardcoded defaults elsewhere).
- `docs/`
  - `c4isr/` – System schema/contract docs (units, tasks, intel, links, timelines, message flows) generated from SDK core.
  - `api/` – API reference for server/db (transport-facing).
  - `ops/` – Operator playbooks/UI usage (separate from technical docs).
- `scripts/` – Dev runners (compose/just) to start db → server (api+services) → ui.
- `examples/` – Minimal runnable examples that import SDK surfaces (per Clanker commandments).

## Ownership rules
- Operational protocols (COT/ATAK/SIDC) live in SDK core adapters/payload builders; they never open sockets or choose transports.
- Transports (HTTP/WS/WebRTC) live in SDK clients; they never encode C4ISR meaning.
- Sigma-server uses SDK core for validation/semantics and SDK clients for db access; its services layer contains sim/OODA loops.
- Sigma-ui only talks to sigma-server surfaces; any operational parsing/rendering calls SDK core helpers, not ad-hoc code.
- Sigma-db is storage-only; domain meaning stays in SDK core; access via SDK clients.

## Components
- **SDK (`sigmac3_sdk`)**: API, base schemas, clients and utility functions. Install locally with `pip install -e sdk/sigmac3-sdk`.
- **Sigma-DB**: Placeholder TinyDB + FastAPI CRUD service (`apps/sigma-db/server.py`). Default data dir `apps/sigma-db/database/`; client shim re-exports `sigmac3_sdk.clients.DBClient`.
- **Sigma-Server**: service host. Operational code lives under `services/`:
  - `services/sim/`: `battlesim.py` Basic test script for testing polling, tasks, moving units
  - `services/ai/`: Experimental agents and helpers, prompts, APP-6 tables, Chroma store, logs, and `experiments/` (legacy scripts may rely on missing `lib.*` shims).
- **Sigma-UI**: Flask app + aiohttp sidecar (WebRTC). Uses SDK schemas/clients; streams via `/ws/stream` on `ui_port + 1`.

## Layout
- `apps/` (`sigma-ui/`, `sigma-server/`, `sigma-db/`)
- `sdk/sigmac3-sdk/` – SDK package (`core/`, `clients/`, `geo/`)
- `configs/` – config samples (`sigma-ui`, `sigma-db`)
- `docs/` – c4isr/api/ops stubs (source of truth is code)
- `examples/` – runnable SDK examples (`templates_demo.py`)
- `scripts/` – dev runner stubs

## Config & data
- UI config: `configs/sigma-ui.sample.ini` (host/port, `data_dir`, `imagery_dir`, `log_dir`). Logging tees stdout/stderr to console and `log_dir/sigma-ui.log` (relative paths resolve from `apps/sigma-ui/`).
- Sources: `apps/sigma-ui/sources.json` owns imagery/stream entries; `files.path` should point at imagery root (`image/`/`video/` subdirs).
- DB config: `configs/sigma-db.sample.json` sets `db_dir` (default `apps/sigma-db/database/`) and allowed collections.
- Seeds/assets: TinyDB JSON seeds under `apps/sigma-db/database/`; APP-6 tables under `apps/sigma-server/services/ai/data/`.

## Runtime details
- UI WebSocket stream: aiohttp sidecar runs on `ui_port + 1` (`/ws/stream`); map JS connects to that port.
- Imagery: served directly from `imagery_dir` (`files.path`); metadata via EXIF (`exiftool`).
- Optional media deps: WebRTC/video routes need `aiortc`, `opencv-python`, `av`; photo metadata uses `exiftool`.

## Quick run (dev)
- Install SDK: `pip install -e sdk/sigmac3-sdk`
- DB: `pip install -r apps/sigma-db/requirements.txt && python apps/sigma-db/server.py --config configs/sigma-db.sample.json`
- Server: `pip install -r apps/sigma-server/requirements.txt` (AI extras: `apps/sigma-server/services/ai/requirements.txt`)
- UI: `pip install -r apps/sigma-ui/requirements.txt && python apps/sigma-ui/main.py`

## Docs / examples / scripts
- Docs stubs live in `docs/` (`c4isr/`, `api/`, `ops/`; `docs/ops/legacy_db_setup.py` is historical).
- Example: `examples/templates_demo.py` (loads SDK templates).
- Scripts: placeholders in `scripts/` for future orchestrators.

## Notes
- Package/distribution name is `sigmac3-sdk` (`sigmac3_sdk` import) to avoid the existing PyPI `sigma-sdk` (a pet store API?!)
