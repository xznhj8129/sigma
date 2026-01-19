"""
Usage:
    python apps/sigma-db/seed_units.py --db-url http://127.0.0.1:5001/api --template-id COMB_BTN --callsign ALPHA --lat 36.530310 --lon -83.21722 --alt 0.0 --faction FRIENDLY
"""
import argparse
import random
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / "sdk" / "sigmac3-sdk"
if SDK_PATH.exists():
    sys.path.insert(0, str(SDK_PATH))

from sigmac3_sdk.clients.db import DBClient
from sigmac3_sdk.core.schema import TemplateLibrary
from sigmac3_sdk.core.units import CabalUnit, ExternalFormation
from sigmac3_sdk.geo import GPSposition, vector_to_gps


def _offset_position(origin: GPSposition, spacing: float) -> GPSposition:
    bearing = random.uniform(0, 360)
    return vector_to_gps(origin, spacing, bearing)


def _spawn_unit_tree(library: TemplateLibrary, template_id: str, *, num: int, callsign: str | None, parent: CabalUnit | None, faction: str, root_pos: GPSposition, units_out: dict) -> CabalUnit:
    template = library.ground_orgs[template_id]
    payload = library.compile_ground_unit(template_id, unit_code=None, uid=None)
    unit_cls = CabalUnit if faction == "FRIENDLY" else ExternalFormation
    unit = unit_cls(template_type=payload["template_type"], unit_template=payload, code=payload["unit_code"])
    unit.num = num
    unit.parent = parent.unit_code if parent else None
    unit.orglevel = parent.orglevel + 1 if parent else 0
    if callsign and not parent:
        unit.callsign = callsign
    elif parent:
        unit.callsign = f"{parent.callsign}-{num}"
    if faction == "HOSTILE":
        unit.faction = faction

    if parent:
        unit.position = _offset_position(parent.position, getattr(unit, "spacing", 0.0))
    else:
        unit.position = root_pos

    unit.get_name()
    units_out[unit.unit_code] = unit

    child_num = 1
    for comp in (template.tac_e_comp, template.sup_e_comp):
        for child_template, count in comp.items():
            for _ in range(count):
                _spawn_unit_tree(
                    library,
                    child_template,
                    num=child_num,
                    callsign=None,
                    parent=unit,
                    faction=faction,
                    root_pos=unit.position,
                    units_out=units_out,
                )
                child_num += 1
    return unit


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed sigma-db with units/enemies using schema templates.")
    parser.add_argument("--db-url", required=True, help="sigma-db base URL, e.g. http://127.0.0.1:5001/api")
    parser.add_argument("--template-id", required=True, help="Ground org template id (from ground_org.json)")
    parser.add_argument("--callsign", required=True, help="Root callsign")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--alt", type=float, required=True)
    parser.add_argument("--faction", choices=["FRIENDLY", "HOSTILE"], required=True)
    args = parser.parse_args()

    library = TemplateLibrary()
    if args.template_id not in library.ground_orgs:
        raise ValueError(f"Unknown template_id {args.template_id}")

    root_pos = GPSposition(args.lat, args.lon, args.alt)
    units: dict[str, CabalUnit] = {}
    root = _spawn_unit_tree(
        library,
        args.template_id,
        num=1,
        callsign=args.callsign,
        parent=None,
        faction=args.faction,
        root_pos=root_pos,
        units_out=units,
    )

    db = DBClient(base_url=args.db_url)
    target_db = "units" if args.faction == "FRIENDLY" else "intel"
    for u in units.values():
        db.insert(target_db, u.as_dict())
    print(f"Inserted {len(units)} {args.faction.lower()} units into {target_db}, root {root.unit_code}")


if __name__ == "__main__":
    main()
