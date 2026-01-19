"""
Usage:
    python examples/templates_demo.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "sdk" / "sigmac3-sdk"))

from sigmac3_sdk.core.schema import TemplateLibrary, UNIT_CATEGORY_LABELS, UNIT_SIZE_LABELS


def main() -> None:
    library = TemplateLibrary()
    mech_company = library.ground_orgs["MECH_COY"]
    print(
        f"MECH_COY category={UNIT_CATEGORY_LABELS[mech_company.category]} {UNIT_SIZE_LABELS[mech_company.size]}")

    payload = library.compile_ground_unit("MECH_COY", unit_code="MECH001")
    print(f"Compiled payload keys: {sorted(payload.keys())[:5]} ... total={len(payload)}")

    schemas = library.schemas()
    print(f"Schemas available: {', '.join(schemas.keys())}")


if __name__ == "__main__":
    main()
