"""Core value objects for plans, steps and runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


@dataclass
class Step:
    """One unit of work in a plan.

    ``action`` names a registered tool. ``inputs`` values may reference earlier
    outputs with ``$step_id.field`` and are resolved by the executor.
    """

    id: str
    action: str
    inputs: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    retries: int = 0
    kind: str = "tool"
    description: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "inputs": dict(self.inputs),
            "depends_on": list(self.depends_on),
            "retries": self.retries,
            "kind": self.kind,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Step":
        return cls(
            id=data["id"],
            action=data["action"],
            inputs=dict(data.get("inputs", {})),
            depends_on=list(data.get("depends_on", [])),
            retries=int(data.get("retries", 0)),
            kind=data.get("kind", "tool"),
            description=data.get("description", ""),
        )


@dataclass
class StepResult:
    step_id: str
    status: Status
    output: object = None
    error: str = ""
    attempts: int = 0
    elapsed_ms: float = 0.0

    def as_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "attempts": self.attempts,
            "elapsed_ms": round(self.elapsed_ms, 3),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StepResult":
        return cls(
            step_id=data["step_id"],
            status=Status(data["status"]),
            output=data.get("output"),
            error=data.get("error", ""),
            attempts=int(data.get("attempts", 0)),
            elapsed_ms=float(data.get("elapsed_ms", 0.0)),
        )


@dataclass
class RunResult:
    goal: str
    order: list[str]
    results: dict[str, StepResult]
    trace: list[dict] = field(default_factory=list)

    @property
    def status(self) -> Status:
        statuses = {r.status for r in self.results.values()}
        if statuses == {Status.OK}:
            return Status.OK
        if statuses == {Status.FAILED}:
            return Status.FAILED
        return Status.SKIPPED

    def as_dict(self) -> dict:
        return {
            "goal": self.goal,
            "status": self.status.value,
            "order": list(self.order),
            "results": {k: v.as_dict() for k, v in self.results.items()},
            "trace": self.trace,
        }


class PlanError(ValueError):
    """Raised when a plan is structurally invalid."""


class BudgetExceeded(RuntimeError):
    """Raised when a run exceeds its step or failure budget."""
