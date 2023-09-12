"""Retries, budgets and run checkpoints."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from ..plan.model import BudgetExceeded, PlanError, RunResult, StepResult, Status


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    backoff_seconds: float = 0.0

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts


@dataclass
class BudgetPolicy:
    max_steps: int = 100
    max_failures: int = 5

    def check(self, executed: int, failures: int) -> None:
        if executed > self.max_steps:
            raise BudgetExceeded(f"step budget exceeded ({self.max_steps})")
        if failures > self.max_failures:
            raise BudgetExceeded(f"failure budget exceeded ({self.max_failures})")


class Checkpoint:
    """Persist completed step results so a crashed run can resume."""

    def __init__(self, path: str):
        self.path = path

    def load(self) -> dict[str, StepResult]:
        if not os.path.exists(self.path):
            return {}
        with open(self.path, encoding="utf-8") as fh:
            data = json.load(fh)
        return {k: StepResult.from_dict(v) for k, v in data.get("results", {}).items()}

    def save(self, run: RunResult) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(run.as_dict(), fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)


def ensure_dependencies(run: RunResult) -> None:
    for result in run.results.values():
        if result.status is Status.FAILED and result.error.startswith("dependency"):
            raise PlanError(result.error)
