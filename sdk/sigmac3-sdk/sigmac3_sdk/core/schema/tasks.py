from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import Position


class TaskKind(str, Enum):
    MOVE = "move"
    ATTACK = "attack"
    ISR = "isr"
    RESUPPLY = "resupply"
    HOLD = "hold"


class TaskPriority(str, Enum):
    IMMEDIATE = "immediate"
    HIGH = "high"
    ROUTINE = "routine"


class TaskStatus(str, Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    COMPLETE = "complete"
    FAILED = "failed"


class GeoPath(BaseModel):
    points: list[Position]

    model_config = ConfigDict(extra="forbid")


class GeoArea(BaseModel):
    vertices: list[Position]

    model_config = ConfigDict(extra="forbid")


class BaseTask(BaseModel):
    task_id: str
    task_type: TaskKind
    unit_code: str
    status: TaskStatus = TaskStatus.NEW
    geometry_id: str | None = None
    start_time: float | None = None
    deadline: float | None = None
    priority: TaskPriority = TaskPriority.ROUTINE
    remarks: str | None = None
    last_update: float | None = None

    model_config = ConfigDict(extra="forbid")


class MoveTask(BaseTask):
    task_type: TaskKind = Field(default=TaskKind.MOVE, frozen=True)
    destination: Position
    route: GeoPath | None = None
    speed_ms: float | None = None
    hold_seconds: float | None = None

    model_config = ConfigDict(extra="forbid")


class AttackTask(BaseTask):
    task_type: TaskKind = Field(default=TaskKind.ATTACK, frozen=True)
    target_unit_code: str | None = None
    target_point: Position | None = None
    munitions: dict[str, int] = Field(default_factory=dict)
    effect: str | None = None
    desired_bda: bool = False

    model_config = ConfigDict(extra="forbid")


class IsrTask(BaseTask):
    task_type: TaskKind = Field(default=TaskKind.ISR, frozen=True)
    area: GeoArea
    dwell_seconds: float | None = None
    sensor_hint: str | None = None

    model_config = ConfigDict(extra="forbid")


class ResupplyTask(BaseTask):
    task_type: TaskKind = Field(default=TaskKind.RESUPPLY, frozen=True)
    destination: Position
    payload: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class HoldTask(BaseTask):
    task_type: TaskKind = Field(default=TaskKind.HOLD, frozen=True)
    location: Position
    radius_m: float | None = None

    model_config = ConfigDict(extra="forbid")


TASK_SCHEMAS = {
    TaskKind.MOVE: MoveTask,
    TaskKind.ATTACK: AttackTask,
    TaskKind.ISR: IsrTask,
    TaskKind.RESUPPLY: ResupplyTask,
    TaskKind.HOLD: HoldTask,
}
