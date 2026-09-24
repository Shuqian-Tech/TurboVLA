"""Immutable domain records shared by the exploration modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

KR260_PLATFORM = "kr260-k26"
KR260_PART = "xck26-sfvc784-2LV-c"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class EvaluationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class DecisionAction(str, Enum):
    CONTINUE = "continue"
    FORK = "fork"
    REPAIR = "repair"
    PROMOTE = "promote"
    FEEDBACK = "feedback"
    STOP = "stop"


@dataclass(frozen=True)
class DesignState:
    design_id: str
    source_revision: str
    hypothesis: str
    change_description: str
    parent_design_id: str | None = None
    target_fpga: str = KR260_PLATFORM
    constraints: dict[str, Any] = field(default_factory=dict)
    created_by: str = "human"
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        source_revision: str,
        hypothesis: str,
        change_description: str,
        parent_design_id: str | None = None,
        constraints: dict[str, Any] | None = None,
        created_by: str = "human",
    ) -> DesignState:
        return cls(
            design_id=new_id("design"),
            parent_design_id=parent_design_id,
            source_revision=source_revision,
            hypothesis=hypothesis,
            change_description=change_description,
            constraints=constraints or {},
            created_by=created_by,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    sha256: str
    path: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Evaluation:
    evaluation_id: str
    design_id: str
    evaluator: str
    phase: str
    status: EvaluationStatus
    command: tuple[str, ...]
    started_at: str
    finished_at: str
    duration_seconds: float
    return_code: int | None
    artifacts: tuple[ArtifactRef, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        result["command"] = list(self.command)
        return result


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    design_id: str
    payload: dict[str, Any]
    evaluation_id: str | None = None
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        event_type: str,
        design_id: str,
        payload: dict[str, Any] | None = None,
        evaluation_id: str | None = None,
    ) -> Event:
        return cls(new_id("event"), event_type, design_id, payload or {}, evaluation_id)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Decision:
    action: DecisionAction
    reason: str
    design_id: str
    requested_evaluators: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["action"] = self.action.value
        result["requested_evaluators"] = list(self.requested_evaluators)
        return result
