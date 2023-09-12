"""Structural interfaces the runtime programs against.

These protocols are deliberately tiny. A planner only has to return a plan; a
tool only has to be callable; an observer only has to accept an event. That
keeps the executor testable with plain lambdas and fakes.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .plan.planner import Plan
from .runtime.trace import Tracer


class Planner(Protocol):
    """Anything that can turn a goal into a validated plan."""

    def plan(self, goal: str) -> Plan:  # pragma: no cover - structural
        ...


class Tool(Protocol):
    """A callable step action."""

    def __call__(self, **kwargs: Any) -> Any:  # pragma: no cover - structural
        ...


@runtime_checkable
class Observer(Protocol):
    """Receives structured trace events."""

    def emit(self, kind: str, step_id: str | None = None, **data: Any) -> None:
        ...  # pragma: no cover - structural


def as_observer(tracer: Tracer | None) -> Observer | None:
    """Adapt a Tracer to the Observer protocol (they share ``emit``)."""
    return tracer
