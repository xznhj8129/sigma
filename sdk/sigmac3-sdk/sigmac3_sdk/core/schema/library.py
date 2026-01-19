import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, TypeAdapter

from .entities import (
    AirOrganizationSchema,
    AirUnitSchema,
    BaseEntity,
    BaseUnit,
    GroundOrganizationSchema,
    GroundUnitSchema,
    IntelTrackSchema,
)
from .models import LinkSchema, SensorSchema, TemplatePathMap

if TYPE_CHECKING:
    from sigmac3_sdk.core.c2 import CabalUnit


DATA_DIR = Path(__file__).resolve().parents[1] / "templates"

TModel = TypeVar("TModel", bound=BaseModel)


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class TemplateLibrary:
    def __init__(
        self,
        data_dir: Path | None = None,
    ):
        root = data_dir if data_dir else DATA_DIR
        self.paths = TemplatePathMap(
            ground_org=root / "ground_org.json",
            air_units=root / "air_units.json",
            links=root / "links.json",
        )

        self.ground_orgs = self._load_templates(
            self.paths.ground_org, GroundOrganizationSchema
        )
        self.air_units = self._load_templates(self.paths.air_units, AirUnitSchema)
        self.links = self._load_templates(self.paths.links, LinkSchema)

    def _load_templates(self, path: Path, model: type[TModel]) -> dict[str, TModel]:
        adapter = TypeAdapter(list[model])
        loaded = adapter.validate_python(_load_json(path))
        return {template.template_id: template for template in loaded}

    def compile_ground_unit(
        self, template_id: str, unit_code: str, uid: str | None = None
    ) -> dict:
        template = self.ground_orgs[template_id]
        payload = template.model_dump(mode="json")
        payload["unit_code"] = unit_code
        payload["uid"] = uid or str(uuid.uuid4())
        payload["template_type"] = template.template_type.value
        payload["type"] = payload["template_type"]
        return payload

    def build_cabal_unit(
        self, template_id: str, unit_code: str, uid: str | None = None
    ) -> "CabalUnit":
        from sigmac3_sdk.core.c2 import CabalUnit
        payload = self.compile_ground_unit(template_id, unit_code, uid)
        unit = CabalUnit(template_type=payload["template_type"], unit_template=payload)
        unit.unit_code = payload["unit_code"]
        unit.uid = payload["uid"]
        unit.get_name()
        return unit

    def schemas(self) -> dict[str, dict]:
        return {
            "base_entity": BaseEntity.model_json_schema(),
            "base_unit": BaseUnit.model_json_schema(),
            "ground_org": GroundOrganizationSchema.model_json_schema(),
            "air_org": AirOrganizationSchema.model_json_schema(),
            "air_unit": AirUnitSchema.model_json_schema(),
            "ground_unit": GroundUnitSchema.model_json_schema(),
            "intel_track": IntelTrackSchema.model_json_schema(),
            "sensor": SensorSchema.model_json_schema(),
            "link": LinkSchema.model_json_schema(),
        }
