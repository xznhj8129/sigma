#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
DB_CONFIG="${1:-}"

if [[ -z "${DB_CONFIG}" ]]; then
  echo "Usage: $0 /absolute/path/to/sigma-db.config.json" >&2
  exit 1
fi

if [[ ! -f "${DB_CONFIG}" ]]; then
  echo "Config not found: ${DB_CONFIG}" >&2
  exit 1
fi

OPENAPI_OUT="${ROOT_DIR}/apps/sigma-frontend/openapi.json"

python - "$ROOT_DIR" "$DB_CONFIG" "$OPENAPI_OUT" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
config_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])

server_path = root / "apps" / "sigma-db" / "server.py"
spec = importlib.util.spec_from_file_location("sigma_db_server", server_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

config = module.load_config(config_path)
app = module.create_app(config)
schema = app.openapi()

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
print(f"wrote OpenAPI schema to {output_path}")
PY

OPENAPI_SPEC_PATH="${OPENAPI_OUT}" npm --prefix "${ROOT_DIR}/apps/sigma-frontend" run generate:api

PYTHONPATH="${ROOT_DIR}/sdk/sigmac3-sdk${PYTHONPATH:+:${PYTHONPATH}}" python - "$ROOT_DIR" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
output_path = root / "docs" / "c4isr" / "schemas.json"

from sigmac3_sdk.core.schema import TemplateLibrary  # noqa: E402

library = TemplateLibrary()
schemas = library.schemas()
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(schemas, indent=2), encoding="utf-8")
print(f"wrote core schema catalog to {output_path}")
PY
