# sigmac3-sdk

Sigma SDK is the shared core for the Sigma C4ISR stack. It owns schemas,
templates, SIDC helpers, geo utilities, and thin transport clients. Nothing in
here opens sockets or encodes app-specific behavior; the server and UI build on
this surface.

## Layout

- `sigmac3_sdk/core/`
  - `schema/` – Pydantic models, enums, entities, tasks, and template loader.
  - `templates/` – JSON template library (ground orgs, air units, links).
  - `c2.py` – CabalUnit/ExternalFormation models plus time/ID helpers.
  - `planning.py` – placeholder hook for shared planning logic.
- `sigmac3_sdk/geo/` – GPSposition helpers and geo math (vector/azimuth/distance).
- `sigmac3_sdk/clients/` – transport-only helpers (TinyDB REST client).

## Quickstart

```python
from sigmac3_sdk.core.schema import TemplateLibrary, UNIT_CATEGORY_LABELS, UNIT_SIZE_LABELS

library = TemplateLibrary()
mech_company = library.ground_orgs["MECH_COY"]
print(f"{UNIT_CATEGORY_LABELS[mech_company.category]} {UNIT_SIZE_LABELS[mech_company.size]}")

payload = library.compile_ground_unit("MECH_COY", unit_code="MECH001")
schemas = library.schemas()
```

Geo helpers:

```python
from sigmac3_sdk.geo import GPSposition, gps_to_vector, vector_to_gps

p1 = GPSposition(36.530310,-83.21722, 0)
p2 = GPSposition(36.7,-83.3, 0)
vec = gps_to_vector(p1, p2)
next_point = vector_to_gps(p1, dist=vec.dist, az=vec.az)
```

DB client:

```python
from sigmac3_sdk.clients.db import DBClient

client = DBClient(base_url="http://localhost:5001/api")
units = client.get_all("units")
```

See `examples/templates_demo.py` for a runnable example seeded with the template
library.
